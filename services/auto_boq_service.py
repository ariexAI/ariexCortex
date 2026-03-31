import re


def parse_size_to_meters(size_str: str):
    numbers = re.findall(r'\d+(?:\.\d+)?', size_str)
    if len(numbers) >= 2:
        l = float(numbers[0])
        b = float(numbers[1])
        if l > 100:
            l = l / 1000
        if b > 100:
            b = b / 1000
        return round(l, 3), round(b, 3)
    return None, None


def build_auto_boq(detected_sizes, calculate_footing_fn, params: dict):

    boq_results = []

    for size in detected_sizes:
        length, breadth = parse_size_to_meters(size)

        if length is None:
            continue

        class AutoFootingInput:
            pass

        footing_input = AutoFootingInput()
        footing_input.number_of_footings = params.get("number_of_footings", 1)
        footing_input.length = length
        footing_input.breadth = breadth
        footing_input.footing_depth = round(length * 0.4, 3)
        footing_input.excavation_depth = params.get("excavation_depth", 1.5)
        footing_input.pcc_thickness = params.get("pcc_thickness", 0.1)
        footing_input.steel_diameter = params.get("steel_diameter", 12.0)
        footing_input.steel_spacing = params.get("steel_spacing", 0.15)
        footing_input.excavation_rate = params.get("excavation_rate", 300.0)
        footing_input.pcc_rate = params.get("pcc_rate", 4500.0)
        footing_input.rcc_rate = params.get("rcc_rate", 7000.0)
        footing_input.steel_rate = params.get("steel_rate", 70.0)

        result = calculate_footing_fn(footing_input)

        boq_results.append({
            "footing_size": size,
            "length_m": length,
            "breadth_m": breadth,
            "boq": result
        })

    return boq_results