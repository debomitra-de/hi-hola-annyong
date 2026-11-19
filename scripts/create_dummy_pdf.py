"""Create a dummy Spanish textbook PDF with 2 chapters for testing."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pymupdf

out = "scripts/spanish_dummy.pdf"
doc = pymupdf.open()

# --- Chapter 1 ---
p1 = doc.new_page()
p1.insert_text((72, 72),  "Capítulo 1 - Saludos y Presentaciones", fontsize=16)
p1.insert_text((72, 110), "En este capítulo aprenderemos a saludar y presentarnos.", fontsize=11)
p1.insert_text((72, 140), "Vocabulario:", fontsize=12)
p1.insert_text((72, 165), "  hola - hello", fontsize=11)
p1.insert_text((72, 185), "  buenos días - good morning", fontsize=11)
p1.insert_text((72, 205), "  buenas tardes - good afternoon", fontsize=11)
p1.insert_text((72, 225), "  me llamo - my name is", fontsize=11)
p1.insert_text((72, 245), "  ¿cómo te llamas? - what is your name?", fontsize=11)
p1.insert_text((72, 265), "  mucho gusto - nice to meet you", fontsize=11)
p1.insert_text((72, 300), "Diálogo:", fontsize=12)
p1.insert_text((72, 325), "  Ana: ¡Hola! Me llamo Ana. ¿Cómo te llamas?", fontsize=11)
p1.insert_text((72, 345), "  Luis: ¡Buenas tardes! Me llamo Luis. Mucho gusto.", fontsize=11)
p1.insert_text((72, 365), "  Ana: Igualmente. ¿De dónde eres, Luis?", fontsize=11)
p1.insert_text((72, 385), "  Luis: Soy de Madrid. ¿Y tú?", fontsize=11)
p1.insert_text((72, 405), "  Ana: Soy de Barcelona.", fontsize=11)
p1.insert_text((72, 440), "Ejercicio: Practica presentarte con un compañero.", fontsize=11)

# --- Chapter 2 ---
p2 = doc.new_page()
p2.insert_text((72, 72),  "Capítulo 2 - En el Restaurante", fontsize=16)
p2.insert_text((72, 110), "En este capítulo aprenderemos a pedir comida en un restaurante.", fontsize=11)
p2.insert_text((72, 140), "Vocabulario:", fontsize=12)
p2.insert_text((72, 165), "  la mesa - the table", fontsize=11)
p2.insert_text((72, 185), "  el menú - the menu", fontsize=11)
p2.insert_text((72, 205), "  quiero pedir - I would like to order", fontsize=11)
p2.insert_text((72, 225), "  la cuenta, por favor - the bill, please", fontsize=11)
p2.insert_text((72, 245), "  ¿qué recomienda? - what do you recommend?", fontsize=11)
p2.insert_text((72, 265), "  está delicioso - it is delicious", fontsize=11)
p2.insert_text((72, 300), "Diálogo:", fontsize=12)
p2.insert_text((72, 325), "  Camarero: Buenas noches, ¿tienen reserva?", fontsize=11)
p2.insert_text((72, 345), "  Cliente: Sí, una mesa para dos personas, por favor.", fontsize=11)
p2.insert_text((72, 365), "  Camarero: ¿Qué desean pedir?", fontsize=11)
p2.insert_text((72, 385), "  Cliente: Quiero la paella y una copa de vino tinto.", fontsize=11)
p2.insert_text((72, 405), "  Camarero: Perfecto. ¿Algo más?", fontsize=11)
p2.insert_text((72, 425), "  Cliente: No, gracias. La cuenta, por favor.", fontsize=11)
p2.insert_text((72, 460), "Ejercicio: Practica pedir comida con un compañero.", fontsize=11)

doc.set_toc([
    [1, "Capítulo 1 - Saludos y Presentaciones", 1],
    [1, "Capítulo 2 - En el Restaurante", 2],
])
doc.save(out)
doc.close()
print(f"Created: {out}")
