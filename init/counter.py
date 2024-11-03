import os

class RunCounter:
    def __init__(self, base_dir):
        self.counter_file = os.path.join(base_dir, '.run_counter')
        
    def increment(self):
        try:
            with open(self.counter_file, 'r') as f:
                count = int(f.read().strip() or '0')
        except FileNotFoundError:
            count = 0
            
        count += 1
        
        with open(self.counter_file, 'w') as f:
            f.write(str(count))
            
        return count 