from sqlalchemy import Column, Integer, String, ForeignKey
try:
    from backend.database import Base
except ImportError:
    from database import Base

class WarehouseStock(Base):
    __tablename__ = "warehouse_stock"

    id = Column(Integer, primary_key=True, autoincrement=True)
    warehouse_id = Column(String, nullable=False, index=True)
    sku_id = Column(String, ForeignKey("skus.sku_id"), nullable=False, index=True)
    available_stock_units = Column(Integer, nullable=False, default=0)
    reserved_stock_units = Column(Integer, nullable=False, default=0)
    free_stock_units = Column(Integer, nullable=False, default=0)
