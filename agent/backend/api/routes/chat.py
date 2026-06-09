"""
聊天相关路由
提供与 Agent 对话的 API 接口
"""

import logging
import uuid
from typing import Dict

from fastapi import APIRouter, HTTPException, status

from api.schemas import ApiResponse, ChatRequest, ChatResponse, ToolCall
from agents.agent import AgentContext, get_agent


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["聊天对话"])

# 会话上下文存储
_sessions: Dict[str, AgentContext] = {}


@router.post(
    "",
    response_model=ApiResponse[ChatResponse],
    status_code=status.HTTP_200_OK,
    summary="与 Agent 对话"
)
async def chat(request: ChatRequest) -> ApiResponse[ChatResponse]:
    """
    与运维 Agent 进行多轮对话
    
    Args:
        request: 对话请求，包含消息和可选的会话 ID
        
    Returns:
        ApiResponse[ChatResponse]: AI 响应
    """
    try:
        logger.info(f"收到对话请求: message={request.message[:50]}..., context_id={request.context_id}")
        
        # 获取或创建会话上下文
        context_id = request.context_id
        if context_id and context_id in _sessions:
            context = _sessions[context_id]
        else:
            context = AgentContext()
            context_id = str(uuid.uuid4())
            _sessions[context_id] = context
        
        # 调用 Agent（使用全局单例避免重复初始化）
        agent = get_agent()
        response = agent.chat(
            user_message=request.message,
            context=context,
        )
        
        # 构建工具调用记录
        tool_calls = []
        for tool_call in response.tool_calls:
            tool_calls.append(ToolCall(
                name=tool_call["tool_name"],
                arguments=tool_call["arguments"],
                result={
                    "success": tool_call.get("success", False),
                    "error": tool_call.get("error"),
                },
            ))
        
        # 构建响应
        chat_response = ChatResponse(
            response=response.content,
            context_id=context_id,
            tool_calls=tool_calls,
        )
        
        logger.info(f"对话完成: context_id={context_id}, tool_calls={len(tool_calls)}")
        
        return ApiResponse[ChatResponse](
            code=200,
            message="success",
            data=chat_response,
        )
        
    except Exception as e:
        logger.error(f"对话处理失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"对话处理失败: {str(e)}",
        )


@router.get(
    "/sessions/{context_id}",
    response_model=ApiResponse[Dict],
    status_code=status.HTTP_200_OK,
    summary="获取会话历史"
)
async def get_session(context_id: str) -> ApiResponse[Dict]:
    """
    获取指定会话的消息历史
    
    Args:
        context_id: 会话 ID
        
    Returns:
        ApiResponse[Dict]: 会话信息
    """
    if context_id not in _sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 {context_id} 不存在",
        )
    
    context = _sessions[context_id]
    return ApiResponse[Dict](
        code=200,
        message="success",
        data={
            "context_id": context_id,
            "message_count": len(context.messages),
        },
    )


@router.delete(
    "/sessions/{context_id}",
    response_model=ApiResponse[Dict],
    status_code=status.HTTP_200_OK,
    summary="清理会话"
)
async def clear_session(context_id: str) -> ApiResponse[Dict]:
    """
    清理指定会话的上下文
    
    Args:
        context_id: 会话 ID
        
    Returns:
        ApiResponse[Dict]: 操作结果
    """
    if context_id in _sessions:
        del _sessions[context_id]
    
    return ApiResponse[Dict](
        code=200,
        message="success",
        data={"cleared": True},
    )
