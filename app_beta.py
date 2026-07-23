# Función para aplicar estilos condicionales y marcar con colores en el visualizador
        def destacar_ordenes_visualizador(row):
          estado = str(row["Estado"])
          tec = str(row["Tecnico"])
          h_conf = str(row["HoraConformidad"])

          # 1. Órdenes Abiertas o sin técnico asignado -> ROJO (Urgente / Pendiente)
          if estado == "Abierta" or tec == "Pendiente de Asignar":
            return [
                "background-color: #f8d7da; color: #721c24;" for _ in row.index
            ]

          # 2. Órdenes Cerradas pendientes de visto bueno -> AMARILLO
          elif estado == "Cerrada" and (
              h_conf == "--:--" or h_conf == "nan" or not h_conf
          ):
            return [
                "background-color: #fff3cd; color: #856404;" for _ in row.index
            ]

          # 3. Órdenes en espera (refacción / externo) -> AZUL
          elif estado == "En Espera":
            return [
                "background-color: #cce5ff; color: #004085;" for _ in row.index
            ]

          # 4. Órdenes con visto bueno completo -> VERDE
          elif h_conf != "--:--" and h_conf != "nan" and h_conf:
            return [
                "background-color: #d4edda; color: #155724;" for _ in row.index
            ]

          else:
            return ["" for _ in row.index]

        try:
          st.dataframe(
              df_f.style.apply(destacar_ordenes_visualizador, axis=1),
              use_container_width=True,
          )
        except Exception:
          st.dataframe(df_f, use_container_width=True)
