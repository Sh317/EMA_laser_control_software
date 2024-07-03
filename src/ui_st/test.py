import datetime

xDat_with_time = []
dat = datetime.datetime.now()
xDat_with_time.append(dat)
change = datetime.timedelta(microseconds=100)
xDat_with_time.append(xDat_with_time[-1] + change)
print(type(dat))
print(xDat_with_time)