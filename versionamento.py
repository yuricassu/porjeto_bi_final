output = BytesIO()
with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
    # Adicionados
    df_added = pd.DataFrame(report["added"], columns=["Adicionados"])
    df_added.to_excel(writer, sheet_name="Adicionados", index=False)

    # Removidos
    df_removed = pd.DataFrame(report["removed"], columns=["Removidos"])
    df_removed.to_excel(writer, sheet_name="Removidos", index=False)

    # Modificados
    if report["modified"]:
        df_mod = pd.DataFrame([
            {
                "Item": m["item"],
                "Alterações": m["alteracoes"],
                "Versão Antiga": str(m["versao_antiga"]),
                "Versão Nova": str(m["versao_nova"])
            }
            for m in report["modified"]
        ])
        df_mod.to_excel(writer, sheet_name="Modificados", index=False)
    else:
        df_mod = None  # não existem modificados

    workbook = writer.book

    # Ajuste de largura das colunas
    for sheet_name in writer.sheets:
        worksheet = writer.sheets[sheet_name]
        if sheet_name == "Modificados" and df_mod is not None:
            df_to_use = df_mod
        elif sheet_name == "Adicionados":
            df_to_use = df_added
        elif sheet_name == "Removidos":
            df_to_use = df_removed
        else:
            continue

        for idx, col in enumerate(df_to_use.columns):
            max_len = max(df_to_use[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(idx, idx, max_len)
