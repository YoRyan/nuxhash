import json

def read_from_file(fd, devices):
    benchmarks = {}
    js = json.load(fd, 'ascii')

    device_instances = lambda s: [d for d in devices if str(d) == s]

    for js_device in js:
        matches = device_instances(js_device)
        if len(matches) > 0:
            # this entry maps to a detected device
            device = matches[0]
            benchmarks[device] = {}
            # read speeds
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

