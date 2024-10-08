from typing import List
from pydantic import BaseModel, Field, model_validator, validator, Extra
from pilot.scene.chat_dashboard.data_preparation.report_schma import ValueItem


class DataNode(BaseModel):
    title: str
    key: str

    type: str = ""
    default_value: str = None
    can_null: str = "YES"
    comment: str = None
    children: List = []


class SqlRunData(BaseModel):
    result_info: str
    run_cost: str
    colunms: List[str]
    values: List


class ChartRunData(BaseModel):
    sql_data: SqlRunData
    chart_values: List[ValueItem]
    chart_type: str
