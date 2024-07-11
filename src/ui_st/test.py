import datetime

    def start_scan(self, start, end, no_scans, time_per_scan):
        self.scan_targets = np.linspace(start, end, no_scans)
        self.time_ps = time_per_scan
        self.scan_time = time_per_scan
        self.scan = 1
        self.j = 0
    
    def scan():
        try:
            if self.scan_time == self.time_ps:
                self.target = self.scan_targets[j]
                delta = self.target - self.wnum
                delta *= 50
                self.laser.tune_reference_cavity(float(self.reference_cavity_tuner_value) - delta)
                #initialize, and one step forward
                self.scam_time = 0
                self.j += 1
            else:
                self.scan_time += self.rate*0.001

        except IndexError:
            self.scan = 0
            self.state = 0

    