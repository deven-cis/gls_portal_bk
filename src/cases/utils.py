# from typing import List
# from fastapi import Depends
# from src.auth.utils import get_current_user
# from src.cases.models import Cases
# from src.users.models import Users
# from src.core.logger import logger

# async def current_user_cases(
#     current_user: dict = Depends(get_current_user),
# ) -> List[Cases]:
#     """
#     Return the cases created by the current authenticated user.
#     """
#     logger.info(f'Listing cases for user: {current_user.get("id")}')
#     user_info = Users.get(current_user.get("id"))
#     return Cases.fetch_records({"entered_by": user_info.entered_by})
