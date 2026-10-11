"""Read public Azure retail rates, never provision resources or read credentials."""

import json
import urllib.parse
import urllib.request
from pathlib import Path

filters = [
    "armRegionName eq 'canadacentral' and armSkuName eq 'Standard_B1ms' and priceType eq 'Consumption'",
    "armRegionName eq 'canadacentral' and serviceName eq 'Storage' and contains(productName, 'Standard SSD')",
]
items = []
for expression in filters:
    url = "https://prices.azure.com/api/retail/prices?" + urllib.parse.urlencode(
        {"$filter": expression, "currencyCode": "USD"}
    )
    with urllib.request.urlopen(url, timeout=30) as response:
        items.extend(json.load(response)["Items"])
Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/azure-retail.json").write_text(json.dumps(items, indent=2))
for item in items:
    if (
        item.get("armSkuName") == "Standard_B1ms"
        and "Windows" not in item["productName"]
        and "Spot" not in item["meterName"]
        and "Low Priority" not in item["meterName"]
    ) or item["meterName"] in {"E4 LRS Disk", "E4 LRS Disk Operations"}:
        print(
            item["productName"],
            item["meterName"],
            item["retailPrice"],
            item["unitOfMeasure"],
            item["currencyCode"],
        )
