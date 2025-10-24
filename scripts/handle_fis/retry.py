"""
重试机制装饰器
"""

import time
import functools
from typing import Callable, Any, Optional
from config import config
from logger import logger
from exceptions import FISLoginException, FISNetworkException, FISTimeoutException


def retry_on_failure(
    max_attempts: Optional[int] = None,
    delay: Optional[float] = None,
    exceptions: tuple = (FISNetworkException, FISTimeoutException, Exception),
    backoff_factor: float = 1.5
):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 重试延迟时间（秒）
        exceptions: 需要重试的异常类型
        backoff_factor: 退避因子，每次重试延迟时间乘以这个因子
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 使用配置中的默认值
            attempts = max_attempts or config.get('retry.max_attempts', 3)
            retry_delay = delay or config.get('retry.retry_delay', 5)
            
            last_exception = None
            
            for attempt in range(attempts):
                try:
                    logger.debug(f"尝试执行 {func.__name__} (第 {attempt + 1} 次)")
                    result = func(*args, **kwargs)
                    
                    if attempt > 0:
                        logger.log_success(f"{func.__name__} 在第 {attempt + 1} 次尝试后成功")
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    attempt_num = attempt + 1
                    
                    if attempt_num >= attempts:
                        logger.log_error(f"{func.__name__} 在 {attempts} 次尝试后仍然失败", e)
                        raise e
                    
                    wait_time = retry_delay * (backoff_factor ** attempt)
                    logger.log_warning(f"{func.__name__} 第 {attempt_num} 次尝试失败: {str(e)}")
                    logger.info(f"等待 {wait_time:.1f} 秒后进行第 {attempt_num + 1} 次重试...")
                    
                    time.sleep(wait_time)
                    
                except Exception as e:
                    # 对于不在重试范围内的异常，直接抛出
                    logger.log_error(f"{func.__name__} 遇到不可重试的异常", e)
                    raise e
            
            # 如果所有重试都失败了，抛出最后一个异常
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def retry_on_network_failure(max_attempts: int = 3, delay: float = 5.0):
    """专门用于网络操作的重试装饰器"""
    return retry_on_failure(
        max_attempts=max_attempts,
        delay=delay,
        exceptions=(FISNetworkException, FISTimeoutException)
    )


def retry_on_element_not_found(max_attempts: int = 3, delay: float = 2.0):
    """专门用于页面元素查找的重试装饰器"""
    from exceptions import FISElementNotFoundException, FISTimeoutException
    return retry_on_failure(
        max_attempts=max_attempts,
        delay=delay,
        exceptions=(FISElementNotFoundException, FISTimeoutException)
    )
