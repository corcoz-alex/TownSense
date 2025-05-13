# Define styles for buttons and other elements

# Purple button style
purple_button_style = """
button {
    background-color: rgb(119, 92, 255) !important;
    color: white !important;
    border-radius: 4px !important;
    padding: 0.5rem 1rem !important;
    font-weight: 600 !important;
    border: none !important;
    transition: all 0.2s ease !important;
}
button:hover {
    background-color: rgb(97, 73, 226) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 10px rgba(119, 92, 255, 0.4) !important;
}
button:active {
    transform: translateY(0) !important;
}
"""

# Radio button style
radio_button_style = """
.st-dy {
    background-color: #775cff;  /* Default background */
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

