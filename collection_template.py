def generar_cromos_mundial_2026():
    cromos = []

    orden = 1

    # Fila superior FIFA / World Cup
    for i in range(0, 20):
        numero = f"{i:02d}"
        cromos.append({
            "id": f"FWC{numero}",
            "seccion": "FIFA World Cup 2026",
            "grupo": "Especial",
            "numero": numero,
            "nombre": f"FIFA World Cup 2026 {numero}",
            "tipo": "especial",
            "orden_album": orden
        })
        orden += 1

    equipos = [
        # Grupo A
        {"grupo": "A", "codigo": "MEX", "nombre": "México"},
        {"grupo": "A", "codigo": "RSA", "nombre": "Sudáfrica"},
        {"grupo": "A", "codigo": "KOR", "nombre": "Corea del Sur"},
        {"grupo": "A", "codigo": "CZE", "nombre": "República Checa"},

        # Grupo B
        {"grupo": "B", "codigo": "CAN", "nombre": "Canadá"},
        {"grupo": "B", "codigo": "BIH", "nombre": "Bosnia y Herzegovina"},
        {"grupo": "B", "codigo": "QAT", "nombre": "Catar"},
        {"grupo": "B", "codigo": "SUI", "nombre": "Suiza"},

        # Grupo C
        {"grupo": "C", "codigo": "BRA", "nombre": "Brasil"},
        {"grupo": "C", "codigo": "MAR", "nombre": "Marruecos"},
        {"grupo": "C", "codigo": "HAI", "nombre": "Haití"},
        {"grupo": "C", "codigo": "SCO", "nombre": "Escocia"},

        # Grupo D
        {"grupo": "D", "codigo": "USA", "nombre": "Estados Unidos"},
        {"grupo": "D", "codigo": "PAR", "nombre": "Paraguay"},
        {"grupo": "D", "codigo": "AUS", "nombre": "Australia"},
        {"grupo": "D", "codigo": "TUR", "nombre": "Turquía"},

        # Grupo E
        {"grupo": "E", "codigo": "GER", "nombre": "Alemania"},
        {"grupo": "E", "codigo": "CUW", "nombre": "Curazao"},
        {"grupo": "E", "codigo": "CIV", "nombre": "Costa de Marfil"},
        {"grupo": "E", "codigo": "ECU", "nombre": "Ecuador"},

        # Grupo F
        {"grupo": "F", "codigo": "NED", "nombre": "Países Bajos"},
        {"grupo": "F", "codigo": "JPN", "nombre": "Japón"},
        {"grupo": "F", "codigo": "SWE", "nombre": "Suecia"},
        {"grupo": "F", "codigo": "TUN", "nombre": "Túnez"},

        # Grupo G
        {"grupo": "G", "codigo": "BEL", "nombre": "Bélgica"},
        {"grupo": "G", "codigo": "EGY", "nombre": "Egipto"},
        {"grupo": "G", "codigo": "IRN", "nombre": "Irán"},
        {"grupo": "G", "codigo": "NZL", "nombre": "Nueva Zelanda"},

        # Grupo H
        {"grupo": "H", "codigo": "ESP", "nombre": "España"},
        {"grupo": "H", "codigo": "CPV", "nombre": "Cabo Verde"},
        {"grupo": "H", "codigo": "KSA", "nombre": "Arabia Saudita"},
        {"grupo": "H", "codigo": "URU", "nombre": "Uruguay"},

        # Grupo I
        {"grupo": "I", "codigo": "FRA", "nombre": "Francia"},
        {"grupo": "I", "codigo": "SEN", "nombre": "Senegal"},
        {"grupo": "I", "codigo": "IRQ", "nombre": "Irak"},
        {"grupo": "I", "codigo": "NOR", "nombre": "Noruega"},

        # Grupo J
        {"grupo": "J", "codigo": "ARG", "nombre": "Argentina"},
        {"grupo": "J", "codigo": "ALG", "nombre": "Argelia"},
        {"grupo": "J", "codigo": "AUT", "nombre": "Austria"},
        {"grupo": "J", "codigo": "JOR", "nombre": "Jordania"},

        # Grupo K
        {"grupo": "K", "codigo": "POR", "nombre": "Portugal"},
        {"grupo": "K", "codigo": "CDD", "nombre": "R. del Congo"},
        {"grupo": "K", "codigo": "UZB", "nombre": "Uzbekistán"},
        {"grupo": "K", "codigo": "COL", "nombre": "Colombia"},

        # Grupo L
        {"grupo": "L", "codigo": "ENG", "nombre": "Inglaterra"},
        {"grupo": "L", "codigo": "CRO", "nombre": "Croacia"},
        {"grupo": "L", "codigo": "GHA", "nombre": "Ghana"},
        {"grupo": "L", "codigo": "PAN", "nombre": "Panamá"},
    ]

    for equipo in equipos:
        for i in range(1, 21):
            numero = f"{i:02d}"
            cromos.append({
                "id": f"{equipo['codigo']}{numero}",
                "seccion": equipo["nombre"],
                "grupo": equipo["grupo"],
                "numero": numero,
                "nombre": f"{equipo['nombre']} {numero}",
                "tipo": "seleccion",
                "orden_album": orden
            })
            orden += 1

    # Fila inferior Coca-Cola
    for i in range(1, 21):
        numero = f"{i:02d}"
        cromos.append({
            "id": f"CC{numero}",
            "seccion": "Coca-Cola",
            "grupo": "Especial",
            "numero": numero,
            "nombre": f"Coca-Cola {numero}",
            "tipo": "patrocinador",
            "orden_album": orden
        })
        orden += 1

    return cromos