class Menu(BaseModel):
    id: int
    cafeteria: str
    date: str
    meals: str
    post_number: Optional[str]
    crawled_at: str

class MenuSimple(BaseModel):
    cafeteria: str
    date: str
    meals: List[str]  # 쉼표로 분리된 메뉴 리스트