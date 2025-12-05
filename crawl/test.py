from sqlite_setup import get_all_menus, get_today_menus, get_menu_by_date

# rows = get_all_menus()
# print(rows)

# row = get_today_menus()
# print(row)

row = get_menu_by_date('12월 5일')
print(row)