from __future__ import annotations

import json
import math
from itertools import zip_longest


MAX_WEIGHT_OPTIONS = 24
MAX_WEIGHT_LABEL_LENGTH = 40


def _row_value(row, key, default=None):
    if row is None:
        return default

    if isinstance(row, dict):
        return row.get(key, default)

    try:
        return row[key]
    except (IndexError, KeyError, TypeError):
        return default


def parse_decimal_price(raw_value):
    value = str(raw_value or "").strip()

    if not value:
        return None

    try:
        price = float(value.replace(",", "."))
    except ValueError:
        return None

    if not math.isfinite(price) or price < 0:
        return None

    return price


def normalize_weight_label(raw_label):
    label = " ".join(str(raw_label or "").strip().split())
    return label[:MAX_WEIGHT_LABEL_LENGTH]


def normalize_weight_options_from_form(labels, prices):
    options = []
    seen_labels = set()

    for raw_label, raw_price in zip_longest(labels or [], prices or [], fillvalue=""):
        label = normalize_weight_label(raw_label)
        price_value = str(raw_price or "").strip()

        if not label and not price_value:
            continue

        price = parse_decimal_price(price_value)
        if not label or price is None:
            raise ValueError("invalid_weight_option")

        label_key = label.casefold()
        if label_key in seen_labels:
            raise ValueError("duplicate_weight_option")

        seen_labels.add(label_key)
        options.append({"label": label, "price": price})

        if len(options) >= MAX_WEIGHT_OPTIONS:
            break

    return options


def encode_weight_options(options):
    return json.dumps(options or [], ensure_ascii=False, separators=(",", ":"))


def decode_weight_options(raw_options):
    if not raw_options:
        return []

    if isinstance(raw_options, list):
        payload = raw_options
    else:
        try:
            payload = json.loads(str(raw_options))
        except (TypeError, ValueError, json.JSONDecodeError):
            return []

    if not isinstance(payload, list):
        return []

    options = []
    seen_labels = set()

    for option in payload:
        if not isinstance(option, dict):
            continue

        label = normalize_weight_label(option.get("label"))
        price = parse_decimal_price(option.get("price"))
        label_key = label.casefold()

        if not label or price is None or label_key in seen_labels:
            continue

        seen_labels.add(label_key)
        options.append({"label": label, "price": price})

        if len(options) >= MAX_WEIGHT_OPTIONS:
            break

    return options


def get_product_weight_options(product):
    return decode_weight_options(_row_value(product, "weight_options", "[]"))


def product_display_price(product):
    options = get_product_weight_options(product)
    if options:
        return options[0]["price"]

    price = parse_decimal_price(_row_value(product, "price", 0))
    return price if price is not None else 0


def find_weight_option(options, requested_label):
    requested = normalize_weight_label(requested_label).casefold()

    if not requested:
        return None

    for option in options:
        if option["label"].casefold() == requested:
            return option

    return None

