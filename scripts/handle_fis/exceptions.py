"""
自定义异常类
"""


class FISLoginException(Exception):
    """FIS登录基础异常"""
    pass


class FISNetworkException(FISLoginException):
    """网络相关异常"""
    pass


class FISElementNotFoundException(FISLoginException):
    """页面元素未找到异常"""
    pass


class FISAuthenticationException(FISLoginException):
    """认证失败异常"""
    pass


class FISCookieException(FISLoginException):
    """Cookie相关异常"""
    pass


class FISConfigurationException(FISLoginException):
    """配置相关异常"""
    pass


class FISTimeoutException(FISLoginException):
    """超时异常"""
    pass
