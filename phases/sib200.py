"""The five phases of the SIB-200 test.

A phase is a plain Python function. The engine calls it with `measurements`
and the plugs it asks for by name (the names come from `plugs:` in
procedure.yaml). The phase reads the instrument and stores a number. It never
decides pass or fail: the limits in procedure.yaml do that.

If you come from TestStand: a phase is a Step, `measurements.x = ...` fills a
Numeric Limit Test, and the limits sit in the YAML next to the step.
"""

import time  # to space out the readings

# Keys the panels read but that the code writes in a loop with setattr()
# (show_digits, temperature_log). `tofupilot validate` only recognises a
# key written out as `ui.KEY = ...`, so they are listed here once:
#   ui.v0 = ui.v1 = ui.v2 = ui.v3 = ui.a0 = ui.a1 = ui.a2 = ui.a3 =  (panels/psu.html)
#   ui.p0 = ui.p1 = ui.p2 = ui.p3 = ui.p4 = ui.p5 = ui.p6 = ui.p7 = ui.p8 = ui.p9 =
#   ui.p10 = ui.p11 = ui.p12 = ui.p13 = ui.p14 = ui.p15 = ui.p16 = ui.p17 = ui.p18 = ui.p19 =
#   ui.p20 = ui.p21 = ui.p22 = ui.p23 = ui.p24 = ui.p25 = ui.p26 = ui.p27 = ui.p28 = ui.p29 =
#   ui.p30 = ui.p31 = ui.p32 = ui.p33 = ui.p34 = ui.p35 = ui.p36 = ui.p37 = ui.p38 = ui.p39 =
#   ui.p40 = ui.p41 = ui.p42 = ui.p43 = ui.p44 = ui.p45 = ui.p46 = ui.p47 = ui.p48 = ui.p49 =
#   ui.p50 = ui.p51 = ui.p52 = ui.p53 = ui.p54 = ui.p55 = ui.p56 = ui.p57 = ui.p58 = ui.p59 =
#   ui.p60 = ui.p61 = ui.p62 = ui.p63 = ui.p64 = ui.p65 = ui.p66 = ui.p67 = ui.p68 = ui.p69 =
#   ui.p70 = ui.p71 = ui.p72 = ui.p73 = ui.p74 = ui.p75 = ui.p76 = ui.p77 = ui.p78 = ui.p79 =
#   ui.p80 = ui.p81 = ui.p82 = ui.p83 = ui.p84 = ui.p85 = ui.p86 = ui.p87 = ui.p88 = ui.p89 =
#   ui.p90 = ui.p91 = ui.p92 = ui.p93 = ui.p94 = ui.p95 = ui.p96 = ui.p97 = ui.p98 = ui.p99 =  (panels/temperature.html)


def show_digits(ui, prefix, text):
    """Light a seven-segment display of the panel: "24.00" sets ui.v0 = "2",
    ui.v1 = "4", ui.v2 = "0", ui.v3 = "0". The decimal point is drawn by the panel."""
    for k, char in enumerate(text.replace(".", "")):
        setattr(ui, f"{prefix}{k}", char)


def power_on(measurements, psu, log, ui):
    # The panel panels/psu.html shows a bench power supply. Everything written
    # to ui.* is only for the screen: it is never recorded.
    idle = psu.read_current_ma()                    # what the board will draw at 24 V
    ui.output = True                                # the OUTPUT LED
    psu.enable()
    for step in range(1, 25):                       # ramp 0 -> 24 V, like turning the knob
        volts = step * 1.0
        psu.set_voltage(volts)
        ui.volts = volts                            # turns the knob on the panel
        show_digits(ui, "v", f"{volts:05.2f}")
        show_digits(ui, "a", f"{idle * volts / 24:05.1f}")
        time.sleep(0.1)                             # slow enough to watch the knob turn
    ui.cv = True                                    # constant-voltage LED: settled at 24 V

    current = psu.read_current_ma()
    measurements.idle_current = current             # the recorded value, judged by the limit
    show_digits(ui, "a", f"{current:05.1f}")
    log.info(f"idle current {current} mA")
    time.sleep(1.5)                                 # leave the result on screen a moment


def rail_3v3(measurements, dmm, log):
    measurements.rail_3v3 = dmm.read_volts()        # the engine compares it to 3.2 .. 3.4 V
    log.info(f"3.3 V rail {measurements.rail_3v3} V")


def flash_firmware(measurements, programmer, log):
    programmer.flash("sib200_v2.1.0.hex")
    measurements.firmware_version = programmer.read_version()
    log.info(f"firmware {measurements.firmware_version}")


def read_sensor(measurements, sensor, log):
    measurements.temp_c = sensor.read_temp_c(0x48)  # 0x48: the sensor's I2C address
    log.info(f"temperature {measurements.temp_c} °C")


def temperature_log(measurements, sensor, log, ui):
    # 100 readings, one every 50 ms: 5 seconds in total.
    # The panel panels/temperature.html draws them live: point i is ui.p<i>.
    times = []
    temps = []
    start = time.monotonic()
    for i in range(100):
        times.append(round(time.monotonic() - start, 3))
        temps.append(sensor.read_temp_c(0x48))
        if i == 0:
            ui.center = round(temps[0], 1)      # the chart is centred on the first reading
        setattr(ui, f"p{i}", temps[-1])         # one more point on the chart
        ui.temp = temps[-1]                     # the big live value
        ui.n = i + 1                            # samples so far
        ui.tmin = min(temps)                    # the blue and red dashed lines
        ui.tmax = max(temps)
        next_reading = start + (i + 1) * 0.05   # when the next reading is due
        time.sleep(max(0, next_reading - time.monotonic()))

    # A curve: time on the x axis, temperature on the y axis.
    measurements.temperature_log.x_axis = times
    measurements.temperature_log.y_axis.temperature = temps

    # The limits in procedure.yaml check the lowest and highest values.
    measurements.temperature_log.y_axis.temperature.aggregations.min = min(temps)
    measurements.temperature_log.y_axis.temperature.aggregations.max = max(temps)
    log.info(f"temperature from {min(temps)} to {max(temps)} °C")
