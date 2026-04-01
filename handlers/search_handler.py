"""
搜索处理器 - 包含搜索和多轮对话逻辑
"""
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
from astrbot.core.utils.session_waiter import session_waiter, SessionController
from ..services import (
    fetch_search_results, fetch_article, build_article_message,
    format_search_results, format_help_message,
    SEARCH_TAG_IDS, SEARCH_ORDER_TYPES,
    SessionManager, SearchSession
)
from .article_handler import extract_url_from_message


def parse_search_params(message: str) -> tuple:
    """解析搜索参数，返回 (keyword, tag_type, order)"""
    parts = message.split()
    keyword = parts[0] if parts else ''
    tag_type = None
    order = ''

    if len(parts) >= 2:
        if parts[1] in SEARCH_TAG_IDS:
            tag_type = parts[1]
        elif parts[1] == '最新':
            order = SEARCH_ORDER_TYPES.get('最新', 'create')

    if len(parts) >= 3 and parts[2] == '最新':
        order = SEARCH_ORDER_TYPES.get('最新', 'create')

    return keyword, tag_type, order


async def handle_search(event: AstrMessageEvent, message: str, session_manager: SessionManager):
    """处理搜索请求，启动多轮对话"""
    sender_id = event.get_sender_id()

    # 检查是否有未完成的会话
    if session_manager.exists(sender_id):
        yield event.plain_result("你有未完成的搜索会话，请继续选择或发送'退出'")
        return

    # 无参数：显示帮助
    if not message:
        yield event.plain_result(format_help_message())
        return

    # 检测是否为链接
    url = extract_url_from_message(message)
    if url:
        from .article_handler import handle_article_url
        async for result in handle_article_url(event, url):
            yield result
        return

    # 解析搜索参数
    keyword, tag_type, order = parse_search_params(message)

    # 执行搜索
    try:
        search_info = keyword
        if tag_type:
            search_info += f" | 筛选: {tag_type}"
        if order:
            search_info += " | 排序: 最新"
        yield event.plain_result(f"正在搜索: {search_info}...")

        result = await fetch_search_results(keyword, page=1, tag_type=tag_type, order=order)

        if not result.items:
            yield event.plain_result(f"未找到相关文章: {search_info}")
            return

        # 保存会话状态
        session = SearchSession(
            keyword=keyword,
            tag_type=tag_type,
            order=order,
            current_page=1,
            total_pages=result.total_pages,
            log_id=result.log_id,
            session_id=result.session_id
        )
        session_manager.set(sender_id, session)

        logger.info(f"Saved session for {sender_id}: log_id={result.log_id}, session_id={result.session_id}")

        # 显示搜索结果
        response = format_search_results(result, keyword, 1, tag_type, order)
        yield event.plain_result(response)

        # 启动会话等待
        async for result in handle_search_session(event, sender_id, session_manager):
            yield result

    except Exception as e:
        logger.error(f"Search failed: {e}")
        yield event.plain_result(f"搜索失败: {str(e)}")


async def handle_search_session(event: AstrMessageEvent, sender_id: str, session_manager: SessionManager):
    """处理多轮搜索对话"""
    @session_waiter(timeout=60, record_history_chains=False)
    async def select_article(controller: SessionController, ev: AstrMessageEvent):
        user_msg = ev.message_str.strip()

        # 退出
        if user_msg == "退出":
            session_manager.remove(sender_id)
            await ev.send(ev.plain_result("已退出"))
            controller.stop()
            return

        session = session_manager.get(sender_id)
        if not session:
            await ev.send(ev.plain_result("会话已失效，请重新搜索"))
            controller.stop()
            return

        # 返回搜索结果
        if user_msg in ("返回", "back"):
            await _handle_return(ev, controller, session, session_manager, sender_id)
            return

        # 翻页
        if user_msg in ("下一页", "next"):
            await _handle_next_page(ev, controller, session, session_manager, sender_id)
            return

        if user_msg in ("上一页", "prev"):
            await _handle_prev_page(ev, controller, session, session_manager, sender_id)
            return

        # 选择文章
        try:
            index = int(user_msg)
            await _handle_select_article(ev, controller, session, session_manager, sender_id, index)
        except ValueError:
            # 检查是否是新的搜索命令
            if user_msg.startswith('牛客'):
                session_manager.remove(sender_id)
                await ev.send(ev.plain_result("已退出，开始新搜索..."))
                controller.stop()
                return

            # 不符合格式的输入，自动退出
            session_manager.remove(sender_id)
            await ev.send(ev.plain_result("输入无效，已自动退出搜索"))
            controller.stop()
        except Exception as e:
            await ev.send(ev.plain_result(f"获取失败: {e}"))
            controller.keep(timeout=60, reset_timeout=True)

    try:
        await select_article(event)
    except TimeoutError:
        session_manager.remove(sender_id)
        yield event.plain_result("会话超时，已退出")
    finally:
        event.stop_event()


async def _handle_return(ev: AstrMessageEvent, controller: SessionController,
                         session: SearchSession, session_manager: SessionManager, sender_id: str):
    """处理返回搜索结果"""
    try:
        result = await fetch_search_results(
            session.keyword, page=session.current_page,
            log_id=session.log_id, session_id=session.session_id,
            tag_type=session.tag_type, order=session.order
        )
        response = format_search_results(result, session.keyword, session.current_page,
                                          session.tag_type, session.order)
        await ev.send(ev.plain_result(response))
        controller.keep(timeout=60, reset_timeout=True)
    except Exception as e:
        await ev.send(ev.plain_result(f"返回失败: {e}"))
        controller.keep(timeout=60, reset_timeout=True)


async def _handle_next_page(ev: AstrMessageEvent, controller: SessionController,
                            session: SearchSession, session_manager: SessionManager, sender_id: str):
    """处理下一页"""
    if session.current_page >= session.total_pages:
        await ev.send(ev.plain_result("已是最后一页"))
        controller.keep(timeout=60, reset_timeout=True)
        return

    new_page = session.current_page + 1
    try:
        result = await fetch_search_results(
            session.keyword, page=new_page,
            log_id=session.log_id, session_id=session.session_id,
            tag_type=session.tag_type, order=session.order
        )
        session.current_page = new_page
        session.log_id = result.log_id
        session.session_id = result.session_id
        session_manager.set(sender_id, session)

        response = format_search_results(result, session.keyword, new_page,
                                          session.tag_type, session.order)
        await ev.send(ev.plain_result(response))
        controller.keep(timeout=60, reset_timeout=True)
    except Exception as e:
        await ev.send(ev.plain_result(f"翻页失败: {e}"))
        controller.keep(timeout=60, reset_timeout=True)


async def _handle_prev_page(ev: AstrMessageEvent, controller: SessionController,
                            session: SearchSession, session_manager: SessionManager, sender_id: str):
    """处理上一页"""
    if session.current_page <= 1:
        await ev.send(ev.plain_result("已是第一页"))
        controller.keep(timeout=60, reset_timeout=True)
        return

    new_page = session.current_page - 1
    try:
        result = await fetch_search_results(
            session.keyword, page=new_page,
            log_id=session.log_id, session_id=session.session_id,
            tag_type=session.tag_type, order=session.order
        )
        session.current_page = new_page
        session.log_id = result.log_id
        session.session_id = result.session_id
        session_manager.set(sender_id, session)

        response = format_search_results(result, session.keyword, new_page,
                                          session.tag_type, session.order)
        await ev.send(ev.plain_result(response))
        controller.keep(timeout=60, reset_timeout=True)
    except Exception as e:
        await ev.send(ev.plain_result(f"翻页失败: {e}"))
        controller.keep(timeout=60, reset_timeout=True)


async def _handle_select_article(ev: AstrMessageEvent, controller: SessionController,
                                 session: SearchSession, session_manager: SessionManager,
                                 sender_id: str, index: int):
    """处理选择文章"""
    result = await fetch_search_results(
        session.keyword, page=session.current_page,
        log_id=session.log_id, session_id=session.session_id,
        tag_type=session.tag_type, order=session.order
    )

    if index < 1 or index > len(result.items):
        await ev.send(ev.plain_result(f"无效编号，请选择 1-{len(result.items)}"))
        controller.keep(timeout=60, reset_timeout=True)
        return

    item = result.items[index - 1]
    await ev.send(ev.plain_result("正在获取文章..."))
    article = await fetch_article(item.to_url())
    text, chain = build_article_message(article)
    if chain:
        await ev.send(ev.chain_result(chain))
    else:
        await ev.send(ev.plain_result(text))

    await ev.send(ev.plain_result("输入'返回'继续查看其他文章，或'退出'结束"))
    controller.keep(timeout=60, reset_timeout=True)