import re
import os
from groq import Groq
from services.footing_service import calculate_footing
from services.slab_service import calculate_slab
from models.footing_model import FootingInput

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are Ariex Cortex, a senior civil engineer AI assistant.
You give practical site advice, IS code references, BOQ guidance, and professional explanations.
You remember the conversation history and can refer back to previous messages.
Keep answers concise and practical."""

class SlabInput:
    def __init__(self, length, breadth, thickness):
        self.length = length
        self.breadth = breadth
        self.thickness = thickness
        self.steel_diameter = 12
        self.steel_spacing = 0.15
        self.rcc_rate = 7000
        self.steel_rate = 70

def extract_dimensions(question: str):
    numbers = re.findall(r"\d+\.?\d*", question)
    if len(numbers) >= 3:
        return float(numbers[0]), float(numbers[1]), float(numbers[2])
    return None

def extract_footing_count(question: str):
    match = re.search(r"(\d+)\s*footing", question.lower())
    if match:
        return int(match.group(1))
    return 1

def is_natural_boq(question: str):
    q = question.lower()
    has_footing = "footing" in q
    has_slab = "slab" in q
    has_numbers = bool(re.search(r"\d", q))
    has_trigger = any(word in q for word in [
        "boq", "cost", "estimate", "calculate", "compute",
        "give me", "i need", "how much", "what will"
    ])
    return has_numbers and has_trigger and (has_footing or has_slab)

def process_query(question: str, history: list = []):

    q = question.lower()

    # NATURAL LANGUAGE BOQ
    if is_natural_boq(question) and not ("calculate footing" in q or "calculate slab" in q or "full boq" in q):
        dims = extract_dimensions(question)
        count = extract_footing_count(question)
        has_footing = "footing" in q
        has_slab = "slab" in q
        parts = []
        total = 0

        if has_footing and dims:
            l, w, d = dims
            data = FootingInput(
                number_of_footings=count, length=l, breadth=w,
                footing_depth=d, excavation_depth=1.5, pcc_thickness=0.1,
                steel_diameter=12, steel_spacing=0.15,
                excavation_rate=300, pcc_rate=4500, rcc_rate=7000, steel_rate=70
            )
            result = calculate_footing(data)
            total += result["total_cost"]
            parts.append(
                f"🏗️ FOOTING ({count} nos, {l}m x {w}m x {d}m)\n"
                f"  Volume: {round(result['rcc'], 2)} m3\n"
                f"  Steel: {round(result['steel'], 2)} kg\n"
                f"  Cost: Rs{round(result['total_cost'], 2)}"
            )

        if has_slab:
            all_nums = re.findall(r"\d+\.?\d*", question)
            if has_footing and len(all_nums) >= 5:
                sl, sw = float(all_nums[3]), float(all_nums[4])
                st = 0.15
            elif not has_footing and len(all_nums) >= 2:
                sl, sw = float(all_nums[0]), float(all_nums[1])
                st = float(all_nums[2]) if len(all_nums) >= 3 else 0.15
            else:
                sl, sw, st = (dims[0], dims[1], 0.15) if dims else (5, 4, 0.15)

            slab_data = SlabInput(sl, sw, st)
            slab_result = calculate_slab(slab_data)
            total += slab_result["total_cost"]
            parts.append(
                f"🧱 SLAB ({sl}m x {sw}m x {st}m)\n"
                f"  Volume: {round(slab_result['volume'], 2)} m3\n"
                f"  Steel: {round(slab_result['steel_weight'], 2)} kg\n"
                f"  Cost: Rs{round(slab_result['total_cost'], 2)}"
            )

        if parts:
            answer = "📋 Natural Language BOQ\n━━━━━━━━━━━━━━━━━━━━\n"
            answer += "\n━━━━━━━━━━━━━━━━━━━━\n".join(parts)
            answer += f"\n━━━━━━━━━━━━━━━━━━━━\n💰 GRAND TOTAL: Rs{round(total, 2)}"
            return {"answer": answer, "category": "full_boq"}
        else:
            return {"answer": "Please include dimensions like: 3 footings 2x2x0.5 and slab 5x4", "category": "input_required"}

    # FULL BOQ
    elif ("full boq" in q or "project boq" in q or ("footing" in q and "slab" in q)):
        dims = extract_dimensions(question)
        if dims:
            l, w, d = dims
            footing_data = FootingInput(
                number_of_footings=1, length=l, breadth=w,
                footing_depth=d, excavation_depth=1.5, pcc_thickness=0.1,
                steel_diameter=12, steel_spacing=0.15,
                excavation_rate=300, pcc_rate=4500, rcc_rate=7000, steel_rate=70
            )
            fr = calculate_footing(footing_data)
            slab_data = SlabInput(l, w, 0.15)
            sr = calculate_slab(slab_data)
            grand_total = fr["total_cost"] + sr["total_cost"]
            answer = (
                f"📋 Full BOQ Summary\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📐 Dimensions: {l}m x {w}m x {d}m\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🏗️ FOOTING\n"
                f"  Volume: {round(fr['rcc'], 2)} m3\n"
                f"  Steel: {round(fr['steel'], 2)} kg\n"
                f"  Excavation Cost: Rs{round(fr['excavation_amount'], 2)}\n"
                f"  PCC Cost: Rs{round(fr['pcc_amount'], 2)}\n"
                f"  RCC Cost: Rs{round(fr['rcc_amount'], 2)}\n"
                f"  Steel Cost: Rs{round(fr['steel_amount'], 2)}\n"
                f"  Footing Total: Rs{round(fr['total_cost'], 2)}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🧱 SLAB\n"
                f"  Volume: {round(sr['volume'], 2)} m3\n"
                f"  Steel: {round(sr['steel_weight'], 2)} kg\n"
                f"  Concrete Cost: Rs{round(sr['concrete_amount'], 2)}\n"
                f"  Steel Cost: Rs{round(sr['steel_amount'], 2)}\n"
                f"  Slab Total: Rs{round(sr['total_cost'], 2)}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 GRAND TOTAL: Rs{round(grand_total, 2)}"
            )
            return {"answer": answer, "category": "full_boq"}
        else:
            return {"answer": "Please provide dimensions like: full boq 3 x 3 x 0.5", "category": "input_required"}

    # FOOTING CALCULATION
    elif "footing" in q and ("calculate" in q or "compute" in q):
        dims = extract_dimensions(question)
        if dims:
            l, w, d = dims
            data = FootingInput(
                number_of_footings=1, length=l, breadth=w,
                footing_depth=d, excavation_depth=1.5, pcc_thickness=0.1,
                steel_diameter=12, steel_spacing=0.15,
                excavation_rate=300, pcc_rate=4500, rcc_rate=7000, steel_rate=70
            )
            result = calculate_footing(data)
            answer = (
                f"🏗️ Footing Calculation Complete!\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📐 Dimensions: {l}m x {w}m x {d}m\n"
                f"📦 Concrete Volume: {round(result['rcc'], 2)} m3\n"
                f"⛏️ Excavation Volume: {round(result['excavation'], 2)} m3\n"
                f"🔩 Steel Required: {round(result['steel'], 2)} kg\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💵 Excavation Cost: Rs{round(result['excavation_amount'], 2)}\n"
                f"💵 PCC Cost: Rs{round(result['pcc_amount'], 2)}\n"
                f"💵 RCC Cost: Rs{round(result['rcc_amount'], 2)}\n"
                f"💵 Steel Cost: Rs{round(result['steel_amount'], 2)}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 TOTAL COST: Rs{round(result['total_cost'], 2)}"
            )
            return {"answer": answer, "category": "calculation"}
        else:
            return {"answer": "Please provide dimensions like: Calculate footing 2 x 2 x 0.5", "category": "input_required"}

    # SLAB CALCULATION
    elif "slab" in q and ("calculate" in q or "compute" in q):
        dims = extract_dimensions(question)
        if dims:
            l, w, t = dims
            data = SlabInput(l, w, t)
            result = calculate_slab(data)
            answer = (
                f"🧱 Slab Calculation Complete!\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📐 Dimensions: {l}m x {w}m x {t}m\n"
                f"📦 Concrete Volume: {round(result['volume'], 2)} m3\n"
                f"🔩 Steel Required: {round(result['steel_weight'], 2)} kg\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💵 Concrete Cost: Rs{round(result['concrete_amount'], 2)}\n"
                f"💵 Steel Cost: Rs{round(result['steel_amount'], 2)}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 TOTAL COST: Rs{round(result['total_cost'], 2)}"
            )
            return {"answer": answer, "category": "calculation"}
        else:
            return {"answer": "Please provide dimensions like: Calculate slab 5 x 4 x 0.15", "category": "input_required"}

    # STEEL QUERY
    elif "steel" in q and "calculate" not in q:
        return {
            "answer": (
                "🔩 Steel Info:\n"
                "Standard diameter: 8mm to 32mm\n"
                "Weight formula: D2/162 kg/m\n"
                "Min cover for footing: 50mm (IS 456)\n"
                "Fe415 and Fe500 are most common grades."
            ),
            "category": "engineering"
        }

    # EXCAVATION QUERY
    elif "excavation" in q and "calculate" not in q:
        return {
            "answer": (
                "⛏️ Excavation Info:\n"
                "Depth is typically 1.5x footing depth\n"
                "Add 300mm extra on each side for working space\n"
                "Rate: Rs250 - Rs400 per m3 depending on soil type."
            ),
            "category": "engineering"
        }

    # AI BRAIN WITH MEMORY
    else:
        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": question})

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=1024
            )
            return {
                "answer": response.choices[0].message.content,
                "category": "ai_response"
            }
        except Exception as e:
            return {"answer": f"AI brain error: {str(e)}", "category": "error"}