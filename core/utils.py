import threading
import time

class Debouncer:
    def __init__(self, interval):
        self.interval = interval
        self.timer = None

    def debounce(self, func, *args, **kwargs):
        if self.timer:
            self.timer.cancel()
        
        self.timer = threading.Timer(self.interval, func, args=args, kwargs=kwargs)
        self.timer.start()

# Instância global para usar nas telas
save_debouncer = Debouncer(2.0) # Espera 2 segundos