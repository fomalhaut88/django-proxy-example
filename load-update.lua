wrk.method = "PATCH"
wrk.headers["Content-Type"] = "application/json"
-- curl "http://localhost:8080/data?feed=xy&ix=0&size=50000&col[]=x&col[]=y" > data.json
local f = io.open("data.json", "rb")
wrk.body = f:read("*all")
