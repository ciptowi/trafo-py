from fastapi.responses import JSONResponse

def response_ok(data=None, message="Success", status_code=200):
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "message": message,
            "data": data,
        },
    )

def response_paginate(data=list[any], page=0, size=10, total=0, totalPage=0, message="Success", status_code=200):
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "message": message,
            "data":  data,
            "pagination": {
                "page": page,
                "size": size,
                "totalElement": total,
                "totalPage": totalPage
            }
        },
    )


def response_err(message="Error", status_code=400, data=None):
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "data": data,
        },
    )
