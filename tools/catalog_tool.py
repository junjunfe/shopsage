from domain.models import Product
from repositories.database import Database


class CatalogTool:
    def __init__(self, db: Database): self.db = db
    def get_product_details(self, product_ids: list[str]) -> list[Product]: return self.db.get_products(product_ids)

