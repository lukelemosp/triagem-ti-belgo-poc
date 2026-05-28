import html as _html

# Base64 do logo Belgo (SVG)
_LOGO_B64 = (
    "PHN2ZyB3aWR0aD0iMTQ3IiBoZWlnaHQ9Ijc1IiB2aWV3Qm94PSIwIDAgMTQ3IDc1IiBmaWxsPSJub25lIiB4bWxucz0i"
    "aHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPg0KPGcgY2xpcC1wYXRoPSJ1cmwoI2NsaXAwXzIyMzdfMjQ5KSI+DQo8"
    "ZyBjbGlwLXBhdGg9InVybCgjY2xpcDFfMjIzN18yNDkpIj4NCjxnIGNsaXAtcGF0aD0idXJsKCNjbGlwMl8yMjM3XzI0"
    "OSkiPg0KPHBhdGggZD0iTTEuNjUwNiA0MC44MTcyQzEuNDQ0NTQgNDAuNDE5NSAwLjAzNDE3OTcgMzUuNzYwNiAwLjAz"
    "NDE3OTcgMzYuMjA4VjUwLjQ4OUMwLjAzNDE3OTcgNTIuOTg2NCAyLjAwNDY5IDU1LjA5NjIgNC41MTUzMyA1NS4xNjU4"
    "QzcuMTIwMDEgNTUuMjM3MyA5LjI1NjU2IDUzLjE1OTQgOS4yNTY1NiA1MC41ODQ0VjUwLjE4NDdDOS4yNTY1NiA0OS45"
    "MDA0IDkuMDk4NTEgNDkuNjM5OSA4Ljg0ODQ1IDQ5LjUwMDdDNS40ODc1OSA0Ny42Mjc2IDMuNDc1MDcgNDQuMzQ0NyAx"
    "LjY1MDYgNDAuODE3MloiIGZpbGw9IndoaXRlIi8+DQo8cGF0aCBkPSJNOS4yNTY1MSAxOS4wODY0VjQuNTExMDlDOS4y"
    "NTY1MSAxLjk3OTgxIDcuMTkzOTggLTAuMDcyMjY1NiA0LjY0NzMyIC0wLjA3MjI2NTZDMi4xMDA2NiAtMC4wNzIyNjU2"
    "IDAuMDM2MTMyOCAxLjk3OTgxIDAuMDM2MTMyOCA0LjUxMTA5VjMzLjkzNEMwLjQyMDIzMiAyNy43OTk3IDMuODgxMTIg"
    "MjIuMTkyMyA5LjI1ODUxIDE5LjA4NjRIOS4yNTY1MVoiIGZpbGw9IiNFRDFDMjQiLz4NCjxwYXRoIGQ9Ik0xOC42MTg3"
    "IDI1Ljc3OTlDMjMuNzg4IDI1Ljc3OTkgMjcuOTc5MSAyOS45NDU3IDI3Ljk3OTEgMzUuMDgzOEMyNy45NzkxIDM4LjUx"
    "MTkgMjYuMTEyNiA0MS41MDQ1IDIzLjMzNzkgNDMuMTE5MUMyOC45NjU0IDQwLjA5ODYgMzIuMDIyMiAzMy41NzI2IDMw"
    "LjMzMzcgMjcuMTQ3OUMyOC43MzczIDIxLjA3MzIgMjMuNDc2IDE2LjgxNCAxNy40MTg0IDE2LjYxOTFDMTYuMjU2MSAx"
    "Ni42OTQ3IDE1LjA4MzggMTYuODc5NiAxMy45MTU1IDE3LjE4MzlDMTIuMjQzMSAxNy42MTczIDEwLjY4NDcgMTguMjY1"
    "NiA5LjI1ODMgMTkuMDg4OFYzNS4wODU4QzkuMjU4MyAyOS45NDc3IDEzLjQ0OTQgMjUuNzgxOSAxOC42MTg3IDI1Ljc4"
    "MTlWMjUuNzc5OVoiIGZpbGw9InVybCgjcGFpbnQwX3JhZGlhbF8yMjM3XzI0OSkiLz4NCjxwYXRoIGQ9Ik0zNi42Mjc0"
    "IDMwLjQwNzZDMzQuMzM0OCAyMS42ODIzIDI2LjE0NDcgMTYuMDQ3MSAxNy40MTY0IDE2LjYxNzhDMjMuNDc0IDE2Ljgx"
    "MjcgMjguNzM1MyAyMS4wNjk5IDMwLjMzMTggMjcuMTQ2NkMzMi4wMjAyIDMzLjU3MTIgMjguOTY1NCA0MC4wOTkzIDIz"
    "LjMzNiA0My4xMTc3QzIxLjk0OTYgNDMuOTIzMSAyMC4zMzkyIDQ0LjM4ODQgMTguNjE2NyA0NC4zODg0QzEzLjQ0NzQg"
    "NDQuMzg4NCA5LjI1NjMyIDQwLjIyMjYgOS4yNTYzMiAzNS4wODQ0VjE5LjA4NTRDM04ODA5NCAyMi4xOTE0IDAuNDE4"
    "MDQ1IDI3Ljc5ODggMC4wMzU5NDY1IDMzLjkzMzFDLTAuMDg0MDg0NCAzNS44NDQgMC4wOTM5NjE1IDM3LjgwNjYgMC42"
    "MDgwOTQgMzkuNzU5M0MzLjIwNjc2IDQ5LjY0NTggMTMuMzc1NCA1NS41Njc0IDIzLjMyMTkgNTIuOTg0NEMzMy4yNjg1"
    "IDUwLjQwMTQgMzkuMjI2IDQwLjI5NDIgMzYuNjI3NCAzMC40MDc2WiIgZmlsbD0idXJsKCNwYWludDFfcmFkaWFsXzIy"
    "MzdfMjQ5KSIvPg0KPHBhdGggZD0iTTY4LjcxNzggMzQuMTYxNkM2OC43MTc4IDMyLjAxNDEgNjguNDA3NyAzMC4wNTU1"
    "IDY3Ljc4NzYgMjguMjg1N0M2Ny4xNjc0IDI2LjUxNiA2Ni4yNTcyIDI1LjAwNDggNjUuMDU2OSAyMy43NTIxQzYzLjg1"
    "NjUgMjIuNDk5NCA2Mi4zOTYyIDIxLjUyNSA2MC42NzU3IDIwLjgyOTFDNTguOTU1MyAyMC4xMzMxIDU2Ljk5NDggMTku"
    "Nzg1MiA1NC43OTQyIDE5Ljc4NTJDNTIuODczNyAxOS43ODUyIDUxLjA1MzIgMjAuMDgzNCA0OS4zMzI4IDIwLjY4QzQ3"
    "LjYxMjQgMjEuMjc2NSA0Ni4wOTIgMjIuMTMxNSA0NC43NzE2IDIzLjI0NUM0My40NTEzIDI0LjM1ODYgNDIuMzkxIDI1"
    "LjY5MDggNDEuNTkwOCAyNy4yNDE4QzQwLjc5MDYgMjguNzkyOCA0MC4zNTA1IDMwLjUyMjcgNDAuMjcwNSAzMi40MzE2"
    "QzQwLjIzMDUgMzIuODY5MSA0MC4yMTA0IDMzLjMyNjQgNDAuMjEwNCAzMy44MDM3VjM1Ljk1MTJDNC4yMTA0IDQxLjAw"
    "MTggNDEuNTEwOCA0NC44MTk2IDQ0LjExMTUgNDcuNDA0NkM0Ni41OTAxIDQ5Ljg2ODMgNTAuMTU5IDUxLjE1NDggNTQu"
    "ODE2MiA1MS4yNzAxQzU0Ljg0MjIgNTEuMjcwMSA1NS4yNTQzIDUxLjI3ODEgNTUuNzE2NCA1MS4yNzQxQzYwLjE5NTYg"
    "NTEuMTk0NiA2My4yMzQ0IDUwLjM4OTIgNjYuMDMxMSA0Ny4wMDQ5QzY3LjA1MzQgNDUuNzY4MSA2Ni44NzEzIDQzLjk0"
    "MDcgNjUuNjI3IDQyLjkyNjZDNjQuMzgyNyA0MS45MTA1IDYyLjU0NDIgNDIuMDkxNSA2MS41MjM5IDQzLjMyODNDNjAu"
    "MzM1NiA0NC43Njc5IDU5LjQxNTQgNDUuNDA4MiA1NS42MTg0IDQ1LjQ3NzhDNTUuMzk0NCA0NS40ODE4IDU1LjA1NDMg"
    "NDUuNDg1OCA1NC4zNzAxIDQ1LjQ0MkM1My4yNzE4IDQ1LjM2MDUgNTIuMzExNiA0NS4xNzk1IDUxLjQ5NTQgNDQuODk5"
    "MkM1MC4zMzUxIDQ0LjUwMTUgNDkuNDA0OCA0My45NTQ3IDQ4LjcwNDYgNDMuMjU4N0M0OC4wMDQ1IDQyLjU2MjcgNDcu"
    "NTA0MyA0MS43Mjc2IDQ3LjIwNDMgNDAuNzUzM0M0Ni45MDQyIDM5Ljc3ODkgNDYuNzU0MSAzOC43MTUxIDQ2Ljc1NDEg"
    "MzcuNTYxOEg2OC43MTk4VjM0LjE2MTZINjguNzE3OFoiIGZpbGw9IndoaXRlIi8+DQo8cGF0aCBkPSJNODIuNTYxIDQ1"
    "LjQ5NDFDODAuMDgwMyA0NS40OTQxIDc4Ljg0IDQ0LjMwMSA3OC44NCA0MS45MTQ5VjIyLjkwMTRWMTEuNTczM0M3OC44"
    "NCA5Ljc3OTcyIDc3LjM3NTYgOC4zMjYxNyA3NS41NjkyIDguMzI2MTdDNzMuNzYyNyA4LjMyNjE3IDcyLjI5ODMgOS43"
    "Nzk3MiA3Mi4yOTgzIDExLjU3MzNWMTUuMjYxOVY0My44ODM1QzcyLjI5ODMgNDQuOTU3MiA3Mi40ODg0IDQ1Ljk1MTQg"
    "NzIuODY4NSA0Ni44NjYxQzczLjI0ODYgNDcuNzgwOCA3My43ODg3IDQ4LjU2NjIgNzQuNDg4OSA0OS4yMjI0Qzc1LjE4"
    "OTEgNDkuODc4NiA3Ni4wMDkzIDUwLjM4NTcgNzYuOTQ5NSA1MC43NDM2Qzc3Ljg4OTggNTEuMTAxNSA3OC45MiA1MS4y"
    "ODA1IDgwLjA0MDMgNTEuMjgwNUM4MC43MjA1IDUxLjI4MDUgODEuNTQwNyA1MS4yMTA5IDgyLjUwMSA1MS4wNzE3Qzgz"
    "LjQ2MTIgNTAuOTMyNSA4NC4yNjE0IDUwLjc2MzUgODQuOTAxNiA1MC41NjQ2VjQ1LjQ5NDFIODIuNTYxWiIgZmlsbD0i"
    "d2hpdGUiLz4NCjxwYXRoIGQ9Ik0xMTMuMjQ5IDIxLjkzMjdDMTExLjQ4OSAyMS4xNzcxIDEwOS41NzggMjAuNjMwMiAx"
    "MDcuNTE4IDIwLjI5MjJDMTA1LjQ1NyAxOS45NTQyIDEwMy40NjcgMTkuNzg1MiAxMDEuNTQ2IDE5Ljc4NTJDOTY uNTQ0"
    "OCAxOS43ODUyIDkyLjczMzggMjAuOTc4MiA5MC4xMTMxIDIzLjM2NDNDODcuNDkyNSAyNS43NTA1IDg2LjE4MjEgMjku"
    "NDQ5IDg2LjE4MjEgMzQuNDU5OFYzNy41NjE4Qzg2LjE4MjEgNDEuNTc4NSA4Ny4yNjI0IDQ0Ljc1IDg5LjQyMyA0Ny4w"
    "NzY1QzkxLjU4MzUgNDkuNDAzIDk0LjcyNDMgNTAuNTY2MiA5OC44NDU0IDUwLjU2NjJDMTAwLjQ4NiA1MC41NjYyIDEw"
    "MS45MjYgNTAuMTg4NCAxMDMuMTY3IDQ5LjQzMjhDMTA0LjQwNyA0OC42NzcyIDEwNS41ODcgNDcuNzQyNiAxMDYuNzA3"
    "IDQ2LjYyOTFWNDguODk1OUMxMDYuNzA3IDQ4Ljg5NTkgMTA2LjcwNyA0OC45MDc5IDEwNi43MDcgNDguOTE1OEMxMDYu"
    "NzExIDQ4LjkxNTggMTA2LjcxMyA0OC45MTE4IDEwNi43MTUgNDguOTA5OEMxMDYuNjkzIDUyLjYwNjQgMTA2LjI5NSA1"
    "My41OTY2IDEwNC40MjEgNTQuOTEyOUMxMDMuMDkyIDU1Ljg0NTUgOTcuMjM3IDU3LjU5MTQgOTEuMTExNCA1NC42NDI1"
    "Qzg5LjQ4NyA1My44NjExIDg3LjUzNDUgNTQuNTM1MSA4Ni43NDgzIDU2LjE0OThDODUuOTYyMSA1Ny43NjI0IDg2LjY0"
    "MDIgNTkuNzA1MSA4OC4yNjQ3IDYwLjQ4NjVDOTEuNjczNSA2Mi4xMjcgOTUuMTY2NCA2Mi43NjEzIDk4LjMyMTMgNjIu"
    "NzYxM0MxMDIuNTcgNjIuNzYxMyAxMDYuMjA3IDYxLjYxIDEwOC4xOTIgNjAuMjE2MUMxMTIuODY5IDU2LjkyOTIgMTEz"
    "LjI0OSA1Mi45OTgxIDExMy4yNDkgNDguNTcxOFY0Ny45MjM2VjIxLjkzMjdaTTEwMy4yNTcgNDMuNDA3OEMxMDEuOTk2"
    "IDQ0LjMyMjUgMTAwLjUyNiA0NC43Nzk5IDk4Ljg0NTQgNDQuNzc5OUM5Ny41MjUxIDQ0Ljc3OTkgOTYuNDY0OCA0NC42"
    "MTA4IDk1LjY2NDYgNDQuMjcyOEM5NC44NjQ0IDQzLjkzNDggOTQuMjQ0MiA0My40Mzc3IDkzLjgwNDEgNDIuNzgxNUM5"
    "My4zNjQgNDIuMTI1MyA5My4wNzM5IDQxLjMyOTkgOTIuOTMzOSA0MC4zOTUzQzkyLjc5MzggMzkuNDYwOCA5Mi43MjM4"
    "IDM4LjM5NyA5Mi43MjM4IDM3LjIwMzlWMzQuNTc5MkM5Mi43MjM4IDMyLjkwODkgOTIuODczOSAzMS41MDcgOTMuMTcz"
    "OSAzMC4zNzM2QzkzLjQ3NCAyOS4yNDAyIDkzLjk3NDEgMjguMzE1NiA5NC42NzQzIDI3LjU5OTdDOTUuMzc0NSAyNi44"
    "ODM5IDk2LjI5NDcgMjYuMzY2OSA5Ny40MzUgMjYuMDQ4N0M5OC41NzUzIDI1LjczMDYgOTkuOTg1NyAyNS41NzE1IDEw"
    "MS42NjYgMjUuNTcxNUMxMDIuNjI2IDI1LjU3MTUgMTAzLjQ3NyAyNS42NDExIDEwNC4yMTcgMjUuNzgwM0MxMDQuOTU3"
    "IDI1LjkxOTUgMTA1Ljc4NyAyNi4xNDgyIDEwNi43MDcgMjYuNDY2M1YzNi44MDIyVjQwLjAwNzZDMTA1LjY2NyA0MS4z"
    "NTk3IDEwNC41MTcgNDIuNDkzMSAxMDMuMjU3IDQzLjQwNzhaIiBmaWxsPSJ3aGl0ZSIvPg0KPHBhdGggZD0iTTEzMi4x"
    "MDIgNTEuMjgyMUMxMjkuNzAyIDUxLjI4MjEgMTI3LjU4MSA1MC44NzQ0IDEyNS43NDEgNTAuMDU5MkMxMjMuOSA0OS4y"
    "NDM5IDEyMi4zNiA0OC4xMzA0IDEyMS4xMTkgNDYuNzE4NkMxMTkuODc5IDQ1LjMwNjggMTE4LjkzOSA0My42NDY0IDEx"
    "OC4yOTkgNDEuNzM3NUMxMTcuNjU4IDM5LjgyODYgMTE3LjMzOCAzNy43NjA3IDExNy4zMzggMzUuNTMzNlYzNC40MDAy"
    "QzExNy4zNzggMzIuMjkyNCAxMTcuNzQ4IDMwLjM0MzggMTE4LjQ0OSAyOC41NTQyQzExOS4xNDkgMjYuNzY0NiAxMjAu"
    "MTM5IDI1LjIyMzUgMTIxLjQxOSAyMy45MzExQzEyMi43IDIyLjYzODYgMTI0LjI0IDIxLjYyNDUgMTI2LjA0MSAyMC44"
    "ODg3QzEyNy44NDEgMjAuMTUzIDEyOS44NjIgMTkuNzg1MiAxMzIuMTAyIDE5Ljc4NTJDMTM0LjIyMyAxOS43ODUyIDEz"
    "Ni4xOTMgMjAuMTUzIDEzOC4wMTQgMjAuODg4N0MxMzkuODM0IDIxLjYyNDUgMTQxLjQyNSAyMi42Mjg2IDE0Mi43ODUg"
    "MjMuOTAxMkMxNDQuMTQ1IDI1LjE3MzggMTQ1LjIwNiAyNi43MDQ5IDE0NS45NjYgMjguNDk0NUMxNDYuNzI2IDMwLjI4"
    "NDEgMTQ3LjEwNiAzMi4yMTI5IDE0Ny4xMDYgMzQuMjgwOVYzNS41MzM2QzE0Ny4xMDYgMzcuNzYwNyAxNDYuNzc2IDM5"
    "LjgyODYgMTQ2LjExNiA0MS43Mzc1QzE0NS40NTYgNDMuNjQ2NCAxNDQuNDg1IDQ1LjMwNjggMTQzLjIwNSA0Ni43MTg2"
    "QzE0MS45MjUgNDguMTMwNCAxNDAuMzU0IDQ5LjI0MzkgMTM4LjQ5NCA1MC4wNTkyQzEzNi42MzMgNTAuODc0NCAxMzQu"
    "NTAzIDUxLjI4MjEgMTMyLjEwMiA1MS4yODIxWk0xNDAuOTI0IDM1LjUzMzZWMzQuMzQwNUMxNDAuOTI0IDMxLjcxNTgg"
    "MTQwLjIyNCAyOS41ODgyIDEzOC44MjQgMjcuOTU3NkMxMzcuNDI0IDI2LjMyNzEgMTM1LjIwMyAyNS41MTE5IDEzMi4x"
    "NjIgMjUuNTExOUMxMjkuMTIxIDI1LjUxMTkgMTI2LjkyMSAyNi4zMjcxIDEyNS41NjEgMjcuOTU3NkMxMjQuMiAyOS41"
    "ODgyIDEyMy41MiAzMS43MzU3IDEyMy41MiAzNC40MDAyVjM1Ljc3MjJDMTIzLjUyIDM3LjIwMzkgMTIzLjY0IDM4LjUw"
    "NjMgMTIzLjg4IDM5LjY3OTVDMTIzLjEyIDQwLjg1MjcgMTI0LjU2IDQxLjg3NjcgMTI1LjIgNDIuNzUwNkMxMjUuODQx"
    "IDQzLjYyNjYgMTI2LjcyMSA0NC4zMDI2IDEyNy44NDEgNDQuNzc5OUMxMjguOTYxIDQ1LjI1NzEgMTMwLjQwMiA0NS40"
    "OTU3IDEzMi4xNjIgNDUuNDk1N0MxMzMuOTIzIDQ1LjQ5NTcgMTM1LjM2MyA0NS4yNDcxIDEzNi40ODMgNDQuNzVDMTM3"
    "LjYwNCA0NC4yNTI5IDEzOC40OTQgNDMuNTU3IDEzOS4xNTQgNDIuNjYyMkMxMzkuODE0IDQxLjc2NzQgMTQwLjI3NCA0"
    "MC43MTM1IDE0MC41MzQgMzkuNTAwNUMxNDAuNzk0IDM4LjI4NzYgMTQwLjkyNCAzNi45NjUzIDE0MC45MjQgMzUuNTMz"
    "NloiIGZpbGw9IndoaXRlIi8+DQo8L2c+DQo8L2c+DQo8L2c+DQo8ZGVmcz4NCjxyYWRpYWxHcmFkaWVudCBpZD0icGFp"
    "bnQwX3JhZGlhbF8yMjM3XzI0OSIgY3g9IjAiIGN5PSIwIiByPSIxIiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVz"
    "ZSIgZ3JhZGllbnRUcmFuc2Zvcm09InRyYW5zbGF0ZSgzMC4zNzc3IDM1LjE0OTQpIHNjYWxlKDIzLjg0ODEgMjMuNzA0"
    "MikiPg0KPHN0b3Agb2Zmc2V0PSIwLjE3IiBzdG9wLWNvbG9yPSIjRkRCOTEzIi8+DQo8c3RvcCBvZmZzZXQ9IjAuNjYi"
    "IHN0b3AtY29sb3I9IiNGMzcwMjEiLz4NCjwvcmFkaWFsR3JhZGllbnQ+DQo8cmFkaWFsR3JhZGllbnQgaWQ9InBhaW50"
    "MV9yYWRpYWxfMjIzN18yNDkiIGN4PSIwIiBjeT0iMCIgcj0iMSIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2Ui"
    "IGdyYWRpZW50VHJhbnNmb3JtPSJ0cmFuc2xhdGUoMjIuODkzOCAyNS4zNjQ5KSBzY2FsZSgyMy4xNiAyMy4wMjAyKSI+"
    "DQo8c3RvcCBvZmZzZXQ9IjAuNDEiIHN0b3AtY29sb3I9IiM5NjJGMzQiLz4NCjxzdG9wIG9mZnNldD0iMC45OSIgc3Rv"
    "cC1jb2xvcj0iI0VEMUMyNCIvPg0KPC9yYWRpYWxHcmFkaWVudD4NCjwvZGVmcz4NCjwvc3ZnPg=="
)

BELGO_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Montserrat', 'Segoe UI', sans-serif; }

    .header-box {
        background: #003B4A;
        padding: 0;
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 28px;
        box-shadow: 0 4px 16px rgba(0,59,74,0.18);
    }
    .header-accent {
        height: 5px;
        background: linear-gradient(90deg, #ED1C24 0%, #F37021 50%, #FDB913 100%);
    }
    .header-content {
        padding: 20px 28px 22px 28px;
        color: white;
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .header-text h1 {
        margin: 0;
        font-size: 1.5rem;
        font-weight: 800;
        letter-spacing: -0.01em;
        color: #FFFFFF;
    }
    .header-text p {
        margin: 3px 0 0 0;
        font-size: 0.85rem;
        color: rgba(255,255,255,0.72);
        font-weight: 400;
    }
    .header-tag {
        margin-left: auto;
        background: rgba(255,255,255,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.75rem;
        font-weight: 600;
        color: rgba(255,255,255,0.85);
        white-space: nowrap;
    }

    div[data-testid="stButton"][data-key="btn_arq"] > button {
        background: #E6F4F1 !important;
        border: 1.5px solid #A8C8D0 !important;
        color: #003B4A !important;
        font-size: 1rem !important;
        padding: 3px 10px !important;
        border-radius: 8px !important;
        box-shadow: none !important;
        width: auto !important;
        line-height: 1.3 !important;
        transition: background 0.18s, color 0.18s !important;
    }
    div[data-testid="stButton"][data-key="btn_arq"] > button:hover {
        background: #003B4A !important;
        color: #FFFFFF !important;
        border-color: #003B4A !important;
    }

    div[data-testid="stButton"] > button[kind="primary"],
    div[data-testid="stBaseButton-primary"] {
        background: #ED1C24 !important;
        border: none !important;
        color: white !important;
        font-weight: 700 !important;
        font-family: 'Montserrat', sans-serif !important;
        border-radius: 8px !important;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover,
    div[data-testid="stBaseButton-primary"]:hover {
        background: #C8151C !important;
    }

    .badge-n1 {
        display: inline-block;
        background: #E6F4F1;
        color: #003B4A;
        border: 2px solid #003B4A;
        border-radius: 8px;
        padding: 6px 20px;
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 12px;
        font-family: 'Montserrat', sans-serif;
        letter-spacing: 0.02em;
    }
    .badge-n2 {
        display: inline-block;
        background: #FEE8E8;
        color: #ED1C24;
        border: 2px solid #ED1C24;
        border-radius: 8px;
        padding: 6px 20px;
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 12px;
        font-family: 'Montserrat', sans-serif;
        letter-spacing: 0.02em;
    }

    .result-card {
        background: #FAFBFC;
        border: 1px solid #D6E2E5;
        border-top: 3px solid #003B4A;
        border-radius: 12px;
        padding: 24px 28px;
        animation: fadeIn 0.35s ease;
    }
    .result-label {
        font-size: 0.72rem;
        font-weight: 700;
        color: #003B4A;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
        font-family: 'Montserrat', sans-serif;
    }
    .result-value {
        font-size: 0.95rem;
        color: #1A2E33;
        margin-bottom: 18px;
        line-height: 1.55;
    }
    .acao-n1 {
        background: #E6F4F1;
        border-left: 4px solid #003B4A;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        color: #003B4A;
        font-size: 0.9rem;
        font-weight: 600;
        font-family: 'Montserrat', sans-serif;
    }
    .acao-n2 {
        background: #FEE8E8;
        border-left: 4px solid #ED1C24;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        color: #B8000A;
        font-size: 0.9rem;
        font-weight: 600;
        font-family: 'Montserrat', sans-serif;
    }

    .conf-tooltip {
        position: relative;
        display: inline-flex;
        align-items: center;
        cursor: help;
    }
    .conf-tooltip-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 15px;
        height: 15px;
        background: #7A9EA6;
        border-radius: 50%;
        color: white;
        font-size: 0.62rem;
        font-weight: 800;
        font-style: italic;
        margin-left: 6px;
        line-height: 1;
        flex-shrink: 0;
        vertical-align: middle;
    }
    .conf-tooltip-box {
        visibility: hidden;
        opacity: 0;
        width: 260px;
        background: #1A2E33;
        color: #E8F0F2;
        text-align: left;
        border-radius: 8px;
        padding: 10px 14px;
        position: absolute;
        z-index: 9999;
        bottom: 130%;
        right: 0;
        font-size: 0.78rem;
        line-height: 1.6;
        font-family: 'Montserrat', sans-serif;
        box-shadow: 0 4px 16px rgba(0,0,0,0.35);
        transition: opacity 0.2s ease;
        pointer-events: none;
        white-space: normal;
    }
    .conf-tooltip:hover .conf-tooltip-box { visibility: visible; opacity: 1; }

    .conf-bar-bg {
        background: #D6E2E5;
        border-radius: 999px;
        height: 10px;
        margin-top: 6px;
    }
    .conf-bar-fill-n1 { background: #003B4A; height: 10px; border-radius: 999px; }
    .conf-bar-fill-n2 { background: #ED1C24; height: 10px; border-radius: 999px; }

    .cot-container {
        margin-top: 16px;
        margin-bottom: 28px;
        background: #F7FAFB;
        border: 1px solid #D6E2E5;
        border-radius: 12px;
        padding: 20px 24px;
        animation: fadeIn 0.35s ease;
    }
    .cot-title {
        font-size: 0.78rem;
        font-weight: 700;
        color: #003B4A;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
        font-family: 'Montserrat', sans-serif;
    }
    .cot-subtitle {
        font-size: 0.78rem;
        color: #5A7E88;
        font-style: italic;
        font-family: 'Montserrat', sans-serif;
        margin-bottom: 14px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .cot-steps { position: relative; padding-left: 28px; }
    .cot-steps::before {
        content: '';
        position: absolute;
        left: 7px;
        top: 8px;
        bottom: 8px;
        width: 2px;
        background: #C5D8DC;
    }
    .cot-step { position: relative; margin-bottom: 14px; }
    .cot-step:last-child { margin-bottom: 0; }
    .cot-dot {
        position: absolute;
        left: -24px;
        top: 4px;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #003B4A;
        border: 2px solid #fff;
        box-shadow: 0 0 0 2px #C5D8DC;
    }
    .cot-dot-final { background: #ED1C24; box-shadow: 0 0 0 2px #F5C0C2; }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes shimmer {
        0%   { background-position: -600px 0; }
        100% { background-position:  600px 0; }
    }
    .skeleton-line {
        background: linear-gradient(90deg, #E8F0F2 25%, #C5D8DC 50%, #E8F0F2 75%);
        background-size: 1200px 100%;
        animation: shimmer 1.8s infinite ease-in-out;
        border-radius: 4px;
    }
    @keyframes cot-appear {
        from { opacity: 0; transform: translateX(-12px); }
        to   { opacity: 1; transform: translateX(0); }
    }
    @keyframes cot-dot-pulse {
        0%, 80%, 100% { opacity: 0.2; transform: scale(0.7); }
        40%           { opacity: 1;   transform: scale(1.1); }
    }
    .cot-thinking {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        margin-top: 5px;
    }
    .cot-thinking span {
        display: inline-block;
        width: 7px; height: 7px;
        background: #003B4A;
        border-radius: 50%;
    }
    .cot-thinking span:nth-child(1) { animation: cot-dot-pulse 1.4s ease-in-out infinite 0.0s; }
    .cot-thinking span:nth-child(2) { animation: cot-dot-pulse 1.4s ease-in-out infinite 0.2s; }
    .cot-thinking span:nth-child(3) { animation: cot-dot-pulse 1.4s ease-in-out infinite 0.4s; }
    .cot-label {
        font-size: 0.8rem;
        font-weight: 700;
        color: #003B4A;
        font-family: 'Montserrat', sans-serif;
    }
    .cot-text {
        font-size: 0.83rem;
        color: #3D5A62;
        line-height: 1.5;
        margin-top: 1px;
        font-family: 'Montserrat', sans-serif;
    }

    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
    header     { visibility: hidden; }
</style>
"""


def header_html(title: str = "Agente de Triagem TI", subtitle: str = None, tag: str = None) -> str:
    sub = subtitle or "Agente de triagem exposto via MCP — classifica chamados N1/N2 em tempo real"
    tag_html = f'<span class="header-tag">{_html.escape(tag)}</span>' if tag else ""
    return f"""
<div class="header-box">
  <div class="header-accent"></div>
  <div class="header-content">
    <img src="data:image/svg+xml;base64,{_LOGO_B64}"
         style="height:38px;width:auto;flex-shrink:0;" alt="Belgo" />
    <div style="width:1px;height:36px;background:rgba(255,255,255,0.2);margin:0 4px;flex-shrink:0;"></div>
    <div class="header-text">
      <h1>{_html.escape(title)}</h1>
      <p>{_html.escape(sub)}</p>
    </div>
    {tag_html}
  </div>
</div>
"""


def render_result_card(r: dict) -> str:
    """Retorna o HTML do card de resultado N1/N2/FORA_DE_ESCOPO."""
    nivel = r.get("nivel", "FORA_DE_ESCOPO")
    if nivel not in {"N1", "N2", "FORA_DE_ESCOPO"}:
        nivel = "FORA_DE_ESCOPO"
    fora = nivel == "FORA_DE_ESCOPO"

    sugestao = _html.escape(str(r.get("sugestao", ""))).replace("\n", "<br>")
    acao = _html.escape(str(r.get("acao", "")))
    tempo = _html.escape(str(r.get("tempo", "")))
    try:
        conf = max(0, min(100, int(r.get("confianca", 0))))
    except (TypeError, ValueError):
        conf = 0
    motivo = _html.escape(str(r.get("motivo_confianca", "")))

    if fora:
        return f"""
<div class="result-card" style="border-top-color:#F37021;">
  <span style="display:inline-block;background:#FFF4E5;color:#B45309;border:2px solid #F37021;
    border-radius:8px;padding:6px 20px;font-size:1.4rem;font-weight:800;margin-bottom:12px;
    font-family:'Montserrat',sans-serif;letter-spacing:0.02em;">⚠ Fora do Escopo</span>
  <div style="margin-top:6px;margin-bottom:18px;">
    <div class="result-label">O que foi enviado</div>
    <div class="result-value">{sugestao if sugestao else "Esse chamado não parece ser um problema de TI."}</div>
  </div>
  <div style="background:#FFF4E5;border-left:4px solid #F37021;padding:10px 14px;
    border-radius:0 8px 8px 0;color:#92400E;font-size:0.9rem;font-weight:600;
    font-family:'Montserrat',sans-serif;">
    ⚡ {acao if acao else "Reenviar como chamado de TI válido"}
  </div>
</div>"""

    badge = "badge-n1" if nivel == "N1" else "badge-n2"
    bar = "conf-bar-fill-n1" if nivel == "N1" else "conf-bar-fill-n2"
    acao_cls = "acao-n1" if nivel == "N1" else "acao-n2"
    label = "N1 — Helpdesk" if nivel == "N1" else "N2 — Especialista"
    tempo_html = f"""
  <div style="margin-top:18px;">
    <div class="result-label">Tempo estimado de resolução</div>
    <div class="result-value">{tempo}</div>
  </div>""" if tempo and tempo != "N/A" else ""

    return f"""
<div class="result-card">
  <span class="{badge}">{nivel}</span>&nbsp;&nbsp;
  <span style="font-size:1.1rem;font-weight:600;color:#334155;">{label}</span>
  <div style="margin-top:18px;">
    <div style="display:flex;align-items:center;margin-bottom:4px;">
      <div class="result-label" style="margin-bottom:0;">Confiança da classificação</div>
      <span class="conf-tooltip">
        <span class="conf-tooltip-icon">i</span>
        <span class="conf-tooltip-box">{motivo}</span>
      </span>
    </div>
    <div style="display:flex;align-items:center;gap:12px;">
      <div class="conf-bar-bg" style="flex:1;margin-top:0;">
        <div class="{bar}" style="width:{conf}%;"></div>
      </div>
      <span style="font-weight:700;color:#1E293B;">{conf}%</span>
    </div>
  </div>
  {tempo_html}
  <div style="margin-top:18px;">
    <div class="result-label">Sugestão de resolução</div>
    <div class="result-value">{sugestao}</div>
  </div>
  <div class="{acao_cls}">⚡ {acao}</div>
</div>"""


def render_empty_state() -> str:
    return """
<div style="
    border: 2px dashed #C5D8DC;
    border-radius: 12px;
    padding: 48px 32px;
    text-align: center;
    color: #7A9EA6;
    background: #F7FAFB;
">
    <div style="font-size:2.5rem;margin-bottom:12px;">⚙️</div>
    <div style="font-size:0.97rem;font-family:'Montserrat',sans-serif;font-weight:500;">
        Descreva um chamado de TI ao lado<br>e clique em <strong style="color:#003B4A;">Analisar</strong>
    </div>
</div>"""


def stat_card_html(value: str, label: str, color: str = "#003B4A") -> str:
    return f"""
<div style="background:#FAFBFC;border:1px solid #D6E2E5;border-top:3px solid {color};
     border-radius:10px;padding:16px 20px;">
  <div style="font-size:1.8rem;font-weight:800;color:{color};font-family:'Montserrat',sans-serif;">
    {_html.escape(str(value))}
  </div>
  <div style="font-size:0.78rem;color:#5A7E88;font-family:'Montserrat',sans-serif;margin-top:2px;">
    {_html.escape(label)}
  </div>
</div>"""
