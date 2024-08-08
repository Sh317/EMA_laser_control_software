import time

class PIDController:
    """PID controller that takes process variable and calculates the correction based on parameters and setpoint"""
    def __init__(self, kp, ki, kd, setpoint):
        """Constructor that specifies the p, i, d paramters and the setpoint

        Args:
            kp(float): proportional coefficient
            ki(float): intergal coefficient
            kd(float): derivative coefficient
            setpoint(float): setpoint for wavenumber
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.integral = 0
        self.previous_error = 0
        self.previous_time = time.time()
        self.first_update_call = True

    def update(self, current_value):
        """Calculates the correction
        
        Args:
            current_value(float): Process variable
        
        Returns:
            float: Error between the setpoint and process variable
            float: Correction
        """
        current_time = time.time()
        error = self.setpoint - current_value
        if self.first_update_call: 
            self.first_update_call = False
            derivative = 0.
        else:
            delta_time = current_time - self.previous_time
            self.integral += error * delta_time
            derivative = (error - self.previous_error) / delta_time

        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)

        self.previous_error = error
        self.previous_time = current_time

        return error, output
    
    def new_loop(self):
        """Reset everything for a new PID loop"""
        self.first_update_call = True
        self.integral = 0.
    
    def update_kp(self, new_value):
        """Update proportional gain
        
        Arg:
            new_value(float): New proportional constant
        """
        self.kp = new_value 

    def update_ki(self, new_value):
        """Update intergral gain
        
        Arg:
            new_value(float): New integral constant
        """
        self.ki = new_value 

    def update_kd(self, new_value):
        """Update proportional gain
            
            Arg:
                new_value(float): New proportional constant
            """
        self.kd = new_value 
    
    def update_setpoint(self, new_value):
        """Update the setpoint for PID controller
        
        Arg:
            new_value(float): New setpoint
        """
        self.setpoint = new_value
