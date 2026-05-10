"""Manual seed — базовый каталог топ-30 продуктов с алиасами на RU/EN/PL/DE.

Без этого справочника русский текст-ввод не сработает: USDA знает только
английский, Open Food Facts покрывает в основном брендовые товары
(Coca-Cola, Snickers, ...), а пользователь пишет «куриная грудка 200г».

КБЖУ — округлённые справочные значения, выровненные с USDA Foundation Foods
(в частности, https://fdc.nal.usda.gov для chicken breast raw FDC ID 171477).
В сидинге каждая запись становится FoodItem (source=manual, external_id=
``MANUAL-<slug>``) + N FoodAlias.

Расширение этого списка — задача медэдвайзера через админку (спринт 7+).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ManualFood:
    """Одна запись manual-каталога."""

    slug: str  # уникальный идентификатор внутри manual-семейства, попадает в external_id
    name_en: str
    kcal_100g: float
    protein_100g: float
    fat_100g: float
    carbs_100g: float
    fiber_100g: float | None
    aliases: dict[str, list[str]]  # locale -> [alias, alias, ...]
    serving_g: float | None = None
    brand: str | None = None


# 30 базовых продуктов. Алиасы — несколько вариантов на язык, чтобы fuzzy
# trgm нашёл при разных формулировках («куриная грудка», «грудка курицы»,
# «куриное филе»).
MANUAL_FOODS: list[ManualFood] = [
    # --- Мясо / птица ---
    ManualFood(
        slug="chicken-breast-raw",
        name_en="Chicken breast, raw",
        kcal_100g=165, protein_100g=31, fat_100g=3.6, carbs_100g=0, fiber_100g=0,
        aliases={
            "ru": ["куриная грудка", "грудка курицы", "куриное филе", "филе грудки"],
            "en": ["chicken breast", "chicken fillet"],
            "pl": ["pierś z kurczaka", "filet z kurczaka"],
            "de": ["hähnchenbrust", "hühnerbrust", "hähnchenfilet"],
        },
    ),
    ManualFood(
        slug="beef-ground-raw",
        name_en="Beef, ground, raw",
        kcal_100g=250, protein_100g=26, fat_100g=15, carbs_100g=0, fiber_100g=0,
        aliases={
            "ru": ["говяжий фарш", "фарш говяжий", "фарш из говядины"],
            "en": ["ground beef", "minced beef"],
            "pl": ["mielona wołowina", "wołowina mielona"],
            "de": ["rinderhack", "hackfleisch rind", "rindfleisch hack"],
        },
    ),
    ManualFood(
        slug="pork-chop-raw",
        name_en="Pork chop, raw",
        kcal_100g=242, protein_100g=27, fat_100g=14, carbs_100g=0, fiber_100g=0,
        aliases={
            "ru": ["свинина", "свиная отбивная", "свиной стейк"],
            "en": ["pork chop", "pork loin"],
            "pl": ["schab wieprzowy", "kotlet schabowy"],
            "de": ["schweinekotelett", "schweinefleisch"],
        },
    ),
    ManualFood(
        slug="sausage-pork",
        name_en="Pork sausage",
        kcal_100g=300, protein_100g=12, fat_100g=27, carbs_100g=2, fiber_100g=0,
        aliases={
            "ru": ["сосиски", "сардельки", "колбаса варёная"],
            "en": ["sausage", "pork sausage"],
            "pl": ["kiełbasa", "parówki"],
            "de": ["wurst", "bratwurst", "würstchen"],
        },
    ),
    # --- Рыба ---
    ManualFood(
        slug="salmon-raw",
        name_en="Salmon, Atlantic, raw",
        kcal_100g=208, protein_100g=20, fat_100g=13, carbs_100g=0, fiber_100g=0,
        aliases={
            "ru": ["лосось", "сёмга", "красная рыба"],
            "en": ["salmon", "atlantic salmon"],
            "pl": ["łosoś"],
            "de": ["lachs", "atlantischer lachs"],
        },
    ),
    ManualFood(
        slug="tuna-canned",
        name_en="Tuna, canned in water",
        kcal_100g=116, protein_100g=26, fat_100g=1, carbs_100g=0, fiber_100g=0,
        aliases={
            "ru": ["тунец консервированный", "тунец в собственном соку"],
            "en": ["tuna", "canned tuna"],
            "pl": ["tuńczyk w wodzie", "tuńczyk z puszki"],
            "de": ["thunfisch", "thunfisch in wasser"],
        },
    ),
    # --- Яйца ---
    ManualFood(
        slug="chicken-egg-whole",
        name_en="Chicken egg, whole",
        kcal_100g=143, protein_100g=12.6, fat_100g=9.5, carbs_100g=0.7, fiber_100g=0,
        aliases={
            "ru": ["яйцо", "яйца", "куриное яйцо"],
            "en": ["egg", "chicken egg"],
            "pl": ["jajko", "jajka", "jajko kurze"],
            "de": ["ei", "eier", "hühnerei"],
        },
        serving_g=50,
    ),
    # --- Молочка ---
    ManualFood(
        slug="milk-3-2",
        name_en="Milk, 3.2% fat",
        kcal_100g=60, protein_100g=3, fat_100g=3.2, carbs_100g=4.7, fiber_100g=0,
        aliases={
            "ru": ["молоко", "молоко 3.2", "молоко коровье"],
            "en": ["milk", "whole milk"],
            "pl": ["mleko", "mleko pełne"],
            "de": ["milch", "vollmilch"],
        },
    ),
    ManualFood(
        slug="kefir-2-5",
        name_en="Kefir, 2.5% fat",
        kcal_100g=53, protein_100g=2.9, fat_100g=2.5, carbs_100g=4, fiber_100g=0,
        aliases={
            "ru": ["кефир", "кефир 2.5"],
            "en": ["kefir"],
            "pl": ["kefir"],
            "de": ["kefir"],
        },
    ),
    ManualFood(
        slug="cottage-cheese-5",
        name_en="Cottage cheese, 5% fat",
        kcal_100g=121, protein_100g=17, fat_100g=5, carbs_100g=1.8, fiber_100g=0,
        aliases={
            "ru": ["творог", "творог 5", "творог 5%"],
            "en": ["cottage cheese"],
            "pl": ["twaróg", "ser twarogowy"],
            "de": ["quark", "magerquark"],
        },
    ),
    ManualFood(
        slug="yogurt-natural",
        name_en="Yogurt, natural, 3% fat",
        kcal_100g=61, protein_100g=3.5, fat_100g=3, carbs_100g=4.7, fiber_100g=0,
        aliases={
            "ru": ["йогурт", "йогурт натуральный"],
            "en": ["yogurt", "yoghurt", "natural yogurt"],
            "pl": ["jogurt", "jogurt naturalny"],
            "de": ["joghurt", "naturjoghurt"],
        },
    ),
    ManualFood(
        slug="butter",
        name_en="Butter",
        kcal_100g=717, protein_100g=0.9, fat_100g=81, carbs_100g=0.1, fiber_100g=0,
        aliases={
            "ru": ["масло сливочное", "сливочное масло"],
            "en": ["butter"],
            "pl": ["masło"],
            "de": ["butter"],
        },
    ),
    ManualFood(
        slug="cheese-edam",
        name_en="Cheese, Edam-style",
        kcal_100g=357, protein_100g=25, fat_100g=28, carbs_100g=1.4, fiber_100g=0,
        aliases={
            "ru": ["сыр", "сыр твёрдый", "эдам"],
            "en": ["cheese", "edam cheese", "hard cheese"],
            "pl": ["ser", "ser żółty", "edamski"],
            "de": ["käse", "edamer", "hartkäse"],
        },
    ),
    # --- Крупы / хлеб / макароны ---
    ManualFood(
        slug="rice-white-cooked",
        name_en="Rice, white, cooked",
        kcal_100g=130, protein_100g=2.7, fat_100g=0.3, carbs_100g=28, fiber_100g=0.4,
        aliases={
            "ru": ["рис", "рис варёный", "белый рис"],
            "en": ["rice", "white rice", "cooked rice"],
            "pl": ["ryż", "ryż biały"],
            "de": ["reis", "weißer reis"],
        },
    ),
    ManualFood(
        slug="buckwheat-cooked",
        name_en="Buckwheat, cooked",
        kcal_100g=110, protein_100g=4, fat_100g=1.1, carbs_100g=21, fiber_100g=2.7,
        aliases={
            "ru": ["гречка", "гречневая каша", "греча"],
            "en": ["buckwheat"],
            "pl": ["kasza gryczana", "gryka"],
            "de": ["buchweizen"],
        },
    ),
    ManualFood(
        slug="oatmeal-cooked",
        name_en="Oatmeal, cooked with water",
        kcal_100g=71, protein_100g=2.5, fat_100g=1.5, carbs_100g=12, fiber_100g=1.7,
        aliases={
            "ru": ["овсянка", "овсяная каша", "геркулес"],
            "en": ["oatmeal", "porridge"],
            "pl": ["owsianka", "płatki owsiane"],
            "de": ["haferflocken", "haferbrei"],
        },
    ),
    ManualFood(
        slug="pasta-wheat-cooked",
        name_en="Pasta, wheat, cooked",
        kcal_100g=158, protein_100g=5.8, fat_100g=0.9, carbs_100g=31, fiber_100g=1.8,
        aliases={
            "ru": ["макароны", "паста", "спагетти"],
            "en": ["pasta", "spaghetti"],
            "pl": ["makaron", "spaghetti"],
            "de": ["nudeln", "pasta", "spaghetti"],
        },
    ),
    ManualFood(
        slug="bread-white",
        name_en="Bread, white wheat",
        kcal_100g=265, protein_100g=9, fat_100g=3.2, carbs_100g=49, fiber_100g=2.7,
        aliases={
            "ru": ["хлеб", "хлеб белый", "батон"],
            "en": ["bread", "white bread"],
            "pl": ["chleb", "chleb biały", "bułka"],
            "de": ["brot", "weißbrot", "brötchen"],
        },
    ),
    ManualFood(
        slug="bread-rye",
        name_en="Bread, rye",
        kcal_100g=259, protein_100g=8.5, fat_100g=3.3, carbs_100g=48, fiber_100g=5.8,
        aliases={
            "ru": ["хлеб ржаной", "чёрный хлеб", "ржаной хлеб"],
            "en": ["rye bread", "dark bread"],
            "pl": ["chleb żytni", "chleb razowy"],
            "de": ["roggenbrot", "vollkornbrot"],
        },
    ),
    # --- Овощи ---
    ManualFood(
        slug="potato-boiled",
        name_en="Potato, boiled",
        kcal_100g=87, protein_100g=1.9, fat_100g=0.1, carbs_100g=20, fiber_100g=1.8,
        aliases={
            "ru": ["картошка варёная", "картофель", "варёный картофель"],
            "en": ["potato", "boiled potato"],
            "pl": ["ziemniaki", "kartofle"],
            "de": ["kartoffel", "kartoffeln"],
        },
    ),
    ManualFood(
        slug="tomato",
        name_en="Tomato, raw",
        kcal_100g=18, protein_100g=0.9, fat_100g=0.2, carbs_100g=3.9, fiber_100g=1.2,
        aliases={
            "ru": ["помидор", "томат", "помидоры"],
            "en": ["tomato"],
            "pl": ["pomidor"],
            "de": ["tomate", "tomaten"],
        },
    ),
    ManualFood(
        slug="cucumber",
        name_en="Cucumber, raw",
        kcal_100g=15, protein_100g=0.7, fat_100g=0.1, carbs_100g=3.6, fiber_100g=0.5,
        aliases={
            "ru": ["огурец", "огурцы", "огурец свежий"],
            "en": ["cucumber"],
            "pl": ["ogórek", "ogórki"],
            "de": ["gurke"],
        },
    ),
    ManualFood(
        slug="carrot",
        name_en="Carrot, raw",
        kcal_100g=41, protein_100g=0.9, fat_100g=0.2, carbs_100g=10, fiber_100g=2.8,
        aliases={
            "ru": ["морковь", "морковка"],
            "en": ["carrot"],
            "pl": ["marchew", "marchewka"],
            "de": ["karotte", "möhre"],
        },
    ),
    # --- Фрукты ---
    ManualFood(
        slug="apple",
        name_en="Apple, raw, with skin",
        kcal_100g=52, protein_100g=0.3, fat_100g=0.2, carbs_100g=14, fiber_100g=2.4,
        aliases={
            "ru": ["яблоко", "яблоки"],
            "en": ["apple"],
            "pl": ["jabłko"],
            "de": ["apfel"],
        },
        serving_g=180,
    ),
    ManualFood(
        slug="banana",
        name_en="Banana, raw",
        kcal_100g=89, protein_100g=1.1, fat_100g=0.3, carbs_100g=23, fiber_100g=2.6,
        aliases={
            "ru": ["банан", "бананы"],
            "en": ["banana"],
            "pl": ["banan"],
            "de": ["banane"],
        },
        serving_g=120,
    ),
    # --- Орехи / масла ---
    ManualFood(
        slug="walnut",
        name_en="Walnut",
        kcal_100g=654, protein_100g=15, fat_100g=65, carbs_100g=14, fiber_100g=6.7,
        aliases={
            "ru": ["грецкий орех", "грецкие орехи"],
            "en": ["walnut", "walnuts"],
            "pl": ["orzech włoski", "orzechy włoskie"],
            "de": ["walnuss", "walnüsse"],
        },
    ),
    ManualFood(
        slug="olive-oil",
        name_en="Olive oil, extra virgin",
        kcal_100g=884, protein_100g=0, fat_100g=100, carbs_100g=0, fiber_100g=0,
        aliases={
            "ru": ["оливковое масло"],
            "en": ["olive oil"],
            "pl": ["oliwa z oliwek"],
            "de": ["olivenöl"],
        },
    ),
    # --- Фастфуд / еда дальнобойщиков ---
    ManualFood(
        slug="hotdog",
        name_en="Hot dog with bun and ketchup",
        kcal_100g=247, protein_100g=10, fat_100g=14, carbs_100g=18, fiber_100g=1.5,
        aliases={
            "ru": ["хот-дог", "хотдог"],
            "en": ["hot dog", "hotdog"],
            "pl": ["hot dog", "parówka w bułce"],
            "de": ["hot dog", "hotdog"],
        },
    ),
    ManualFood(
        slug="pizza-margherita",
        name_en="Pizza, Margherita",
        kcal_100g=266, protein_100g=11, fat_100g=10, carbs_100g=33, fiber_100g=2.3,
        aliases={
            "ru": ["пицца", "пицца маргарита"],
            "en": ["pizza", "margherita pizza"],
            "pl": ["pizza", "pizza margherita"],
            "de": ["pizza", "margherita"],
        },
    ),
    ManualFood(
        slug="instant-noodles",
        name_en="Instant noodles, prepared",
        kcal_100g=138, protein_100g=3.5, fat_100g=5.5, carbs_100g=19, fiber_100g=1,
        aliases={
            "ru": ["доширак", "лапша быстрого приготовления", "роллтон"],
            "en": ["instant noodles", "ramen noodles"],
            "pl": ["zupka chińska", "makaron instant"],
            "de": ["instant nudeln", "ramen"],
        },
    ),
]
