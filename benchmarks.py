import json

def read_from_file(fd, devices):
    benchmarks = {}
    js = json.load(fd, 'ascii')

    device_instance = lambda s: [d for d in devices if str(d) == s][0]

    for js_device in js:
        device = device_instance(js_device)
        benchmarks[device] = {}
        js_speeds = js[js_device]
        for algorithm in js_speeds:
            if isinstance(js_speeds[algorithm], list):
                benchmarks[device][algorithm] = js_speeds[algorithm]
            else:
                benchmarks[device][algorithm] = [js_speeds[algorithm]]

    return benchmarks

def write_to_file(fd, benchmarks):
    to_file = {}

    for device in benchmarks:
        to_file[str(device)] = {}
        speeds = benchmarks[device]
        for algorithm in speeds:
            if len(speeds[algorithm]) == 1:
                to_file[str(device)][algorithm] = speeds[algorithm][0]
            else:
                to_file[str(device)][algorithm] = speeds[algorithm]

    json.dump(to_file, fd, indent=4)

