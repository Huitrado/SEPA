// Colores, tipografía y espaciados del diseño SEPA.
// Tailwind lee esta configuración para que clases como "bg-primary" o
// "text-headline-lg" tengan los valores del diseño. Se carga en todas las páginas.
tailwind.config = {
  theme: {
    extend: {
      colors: {
        // Paleta "gris, negro y cian": fondo gris frío claro, tarjetas blancas, texto casi negro,
        // botones negros y un solo acento cian. El semáforo y los estados no cambian.
        "primary": "#0d0d0d",                // títulos y texto fuerte; hover de los botones
        "on-primary": "#ffffff",
        "primary-container": "#1a1a1a",      // botones principales y filtros activos
        "on-primary-container": "#8fd8f2",
        "secondary": "#0077b6",              // acento cian legible: enlaces, etiquetas, "Copiar"
        "on-secondary": "#ffffff",
        "secondary-container": "#cdeffb",    // fondo del acento (sección activa)
        "on-secondary-container": "#00557f",
        "acento": "#00aeef",                 // cian vivo, solo para detalles (líneas, marcas)
        "error": "#ba1a1a",
        "on-error": "#ffffff",
        "error-container": "#ffdad6",
        "on-error-container": "#93000a",
        "background": "#eef0f2",
        "surface": "#eef0f2",
        "surface-variant": "#dfe3e6",
        "surface-container-lowest": "#ffffff",
        "surface-container-low": "#f3f5f6",
        "surface-container": "#e8ebed",
        "surface-container-high": "#dfe3e6",
        "surface-container-highest": "#d5dade",
        "on-surface": "#111111",
        "on-surface-variant": "#50555a",
        "outline": "#868b90",
        "outline-variant": "#cdd2d6",
        // Acento ámbar (avisos y pendientes)
        "tertiary-fixed": "#ffdcc3",
        "on-tertiary-fixed-variant": "#6e3900",
        "on-tertiary-container": "#de7b0e",
        // Semáforo de riesgo (RF-50 a RF-52, RF-61): verde, amarillo y rojo (sin cambios)
        "semaforo-verde": "#1b6e3a",
        "semaforo-verde-fondo": "#d5f2de",
        "semaforo-amarillo": "#7a4d00",
        "semaforo-amarillo-fondo": "#ffe6a8",
        "semaforo-rojo": "#ba1a1a",
        "semaforo-rojo-fondo": "#ffdad6"
      },
      borderRadius: { DEFAULT: "0.25rem", lg: "0.5rem", xl: "0.75rem", full: "9999px" },
      spacing: {
        "space-xs": "0.25rem",
        "space-sm": "0.5rem",
        "space-md": "1rem",
        "space-lg": "1.5rem",
        "space-xl": "2rem",
        "space-2xl": "3rem",
        "gutter": "1.5rem"
      },
      fontFamily: {
        "headline-lg": ["Inter"], "headline-md": ["Inter"], "title-lg": ["Inter"], "label-md": ["Inter"], "label-lg": ["Inter"],
        "body-md": ["Inter"], "body-lg": ["Inter"], "helper-sm": ["Inter"], "caption": ["Inter"]
      },
      fontSize: {
        "headline-lg": ["32px", { lineHeight: "36px", letterSpacing: "-0.03em", fontWeight: "700" }],
        "headline-md": ["22px", { lineHeight: "28px", letterSpacing: "-0.02em", fontWeight: "700" }],
        "title-lg": ["18px", { lineHeight: "24px", letterSpacing: "-0.01em", fontWeight: "600" }],
        "label-md": ["12px", { lineHeight: "16px", letterSpacing: "0.02em", fontWeight: "600" }],
        "label-lg": ["14px", { lineHeight: "20px", letterSpacing: "0.01em", fontWeight: "600" }],
        "body-md": ["14px", { lineHeight: "20px", fontWeight: "400" }],
        "body-lg": ["16px", { lineHeight: "24px", fontWeight: "400" }],
        "helper-sm": ["12px", { lineHeight: "16px", fontWeight: "400" }],
        "caption": ["11px", { lineHeight: "14px", letterSpacing: "0.03em", fontWeight: "500" }]
      }
    }
  }
};
