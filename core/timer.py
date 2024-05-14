from datetime import datetime

class Timer:
    start_global = datetime.now()
    elapsed_global = property(lambda: (datetime.now() - Timer.start_global).total_seconds())
    
    def __init__(self) -> None:
        self.start = datetime.now()
        self.last_update = datetime.now()
        self.curr_update = datetime.now()
        self.dt = (self.curr_update - self.last_update).total_seconds()
        self.elapsed = (self.curr_update - self.start).total_seconds()

    def update(self):
        self.last_update = self.curr_update
        self.curr_update = datetime.now()
        self.dt = (self.curr_update - self.last_update).total_seconds()
        self.elapsed = (self.curr_update - self.start).total_seconds()
