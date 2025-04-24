purple_button_style = """
    button {
        background-color: #775cff;
        color: white;
        border-radius: 6px;
        padding: 8px 16px;
        transition: background-color 0.5s ease-in-out, color 0.5s ease-in-out;
    }
    button:hover {
        background-color: #4f2ef3;
        color: white;
    }
"""

hover_text_purple = """
/* Default color */
details summary div[data-testid="stMarkdownContainer"] p {
    color: black;
    transition: color 0.5s ease-in-out;
}

/* On hover over the expander summary */
details:hover summary div[data-testid="stMarkdownContainer"] p {
    color: #775cff;
    transition: color 0.5s ease-in-out;
}
"""