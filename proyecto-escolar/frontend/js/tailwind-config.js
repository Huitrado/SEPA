// Colores, tipografía y espaciados del diseño SEPA (tomados del diseño original).
// Tailwind lee esta configuración para que clases como "bg-primary" o
// "text-headline-lg" tengan los valores del diseño. Se carga en todas las páginas.
tailwind.config = {
  theme: {
    extend: {
      colors: {
        "primary": "#00173b",
        "on-primary": "#ffffff",
        "primary-container": "#0f2c59",
        "on-primary-container": "#7c94c8",
        "secondary": "#305ea1",
        "on-secondary": "#ffffff",
        "secondary-container": "#8ab4fd",
        "on-secondary-container": "#0b4486",
        "error": "#ba1a1a",
        "on-error": "#ffffff",
        "error-container": "#ffdad6",
        "on-error-container": "#93000a",
        "background": "#f8f9ff",
        "surface": "#f8f9ff",
        "surface-variant": "#d3e4fe",
        "surface-container-lowest": "#ffffff",
        "surface-container-low": "#eff4ff",
        "surface-container": "#e5eeff",
        "surface-container-high": "#dce9ff",
        "surface-container-highest": "#d3e4fe",
        "on-surface": "#0b1c30",
        "on-surface-variant": "#44474f",
        "outline": "#747780",
        "outline-variant": "#c4c6d0"
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
        "headline-lg": ["Inter"], "title-lg": ["Inter"], "label-md": ["Inter"], "label-lg": ["Inter"],
        "body-md": ["Inter"], "body-lg": ["Inter"], "helper-sm": ["Inter"], "caption": ["Inter"]
      },
      fontSize: {
        "headline-lg": ["30px", { lineHeight: "38px", letterSpacing: "-0.015em", fontWeight: "600" }],
        "title-lg": ["18px", { lineHeight: "24px", fontWeight: "600" }],
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
