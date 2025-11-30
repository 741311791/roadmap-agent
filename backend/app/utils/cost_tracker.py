"""
LLM 成本追踪工具
"""
from typing import Dict, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


class CostTracker:
    """LLM 成本追踪器"""
    
    # 模型定价（每 1M tokens，美元）
    # 注意：这些价格需要定期更新
    MODEL_PRICING: Dict[str, Dict[str, float]] = {
        "gpt-4o-mini": {
            "prompt": 0.15,  # $0.15 per 1M prompt tokens
            "completion": 0.60,  # $0.60 per 1M completion tokens
        },
        "gpt-4o": {
            "prompt": 2.50,
            "completion": 10.00,
        },
        "claude-3-5-sonnet-20241022": {
            "prompt": 3.00,
            "completion": 15.00,
        },
    }
    
    def __init__(self):
        self.total_cost: float = 0.0
        self.usage_by_agent: Dict[str, Dict[str, float]] = {}
    
    def track(
        self,
        agent_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """
        追踪一次 LLM 调用的成本
        
        Args:
            agent_id: Agent ID
            model: 模型名称
            prompt_tokens: Prompt tokens 数量
            completion_tokens: Completion tokens 数量
            
        Returns:
            本次调用的成本（美元）
        """
        # 获取模型定价
        pricing = self.MODEL_PRICING.get(model, {})
        prompt_price_per_million = pricing.get("prompt", 0.0)
        completion_price_per_million = pricing.get("completion", 0.0)
        
        # 计算成本
        prompt_cost = (prompt_tokens / 1_000_000) * prompt_price_per_million
        completion_cost = (completion_tokens / 1_000_000) * completion_price_per_million
        total_cost = prompt_cost + completion_cost
        
        # 更新总成本
        self.total_cost += total_cost
        
        # 更新 Agent 使用统计
        if agent_id not in self.usage_by_agent:
            self.usage_by_agent[agent_id] = {
                "total_cost": 0.0,
                "total_tokens": 0,
                "call_count": 0,
            }
        
        self.usage_by_agent[agent_id]["total_cost"] += total_cost
        self.usage_by_agent[agent_id]["total_tokens"] += prompt_tokens + completion_tokens
        self.usage_by_agent[agent_id]["call_count"] += 1
        
        logger.info(
            "cost_tracked",
            agent_id=agent_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=total_cost,
            total_cost_usd=self.total_cost,
        )
        
        return total_cost
    
    def get_total_cost(self) -> float:
        """获取总成本"""
        return self.total_cost
    
    def get_agent_stats(self, agent_id: str) -> Optional[Dict[str, float]]:
        """获取指定 Agent 的统计信息"""
        return self.usage_by_agent.get(agent_id)
    
    def reset(self):
        """重置统计信息"""
        self.total_cost = 0.0
        self.usage_by_agent = {}


# 全局单例
cost_tracker = CostTracker()

