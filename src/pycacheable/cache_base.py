from abc import ABC, abstractmethod


class CacheBase(ABC):
    @abstractmethod
    def get(self, **args):
        pass

    @abstractmethod
    def set(self, **args):
        pass

    @abstractmethod
    def clear(self, **args):
        pass

    @abstractmethod
    def info(self, **args):
        pass
