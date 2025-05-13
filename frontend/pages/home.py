import streamlit as st
import os
import base64
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit.components.v1 import html


def show_home():
    try:
        webm_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.webm")
        with open(webm_path, "rb") as f:
            base64_webm = base64.b64encode(f.read()).decode()

        st.markdown(f"""
            <div style="text-align: center;">
                <video width="750" autoplay loop muted playsinline>
                    <source src="data:video/webm;base64,{base64_webm}" type="video/webm">
                    Your browser does not support the video tag.
                </video>
            </div>
        """, unsafe_allow_html=True)

    except FileNotFoundError:
        st.error("🚫 Could not load homepage animation (logo.webm not found)")

    html("""
    <style>
    .hero-text {
      text-align: center;
      padding: 5vh 0;
      font-family: 'Trebuchet MS', sans-serif;
    }

    .hero-title {
      opacity: 0;
      animation: fadeInHero 1.2s ease 0.5s forwards;
    }

    .hero-subtitle {
      opacity: 0;
      animation: fadeInHero 1.2s ease 0.9s forwards;
    }

    @keyframes fadeInHero {
      from { opacity: 0; transform: translateY(20px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    </style>

    <div class="hero-text">
      <h1 class="hero-title" style="font-size: 3.1rem; font-weight: 800; margin-bottom: 0.5rem;">
        Detect Urban Problems with AI
      </h1>
      <p class="hero-subtitle" style="font-size: 1.50rem; color: gray;">
        Revolutionize how cities stay clean, safe, and efficient in a modern and fun way.
      </p>
    </div>
    """, height=200)

    assets_path = os.path.join(os.path.dirname(__file__), "..", "assets")

    image1_path = os.path.join(assets_path, "urban1.png")
    image2_path = os.path.join(assets_path, "urban2.png")
    image3_path = os.path.join(assets_path, "urban3.png")

    with open(image1_path, "rb") as img_file:
        img1_base64 = base64.b64encode(img_file.read()).decode("utf-8")

    with open(image2_path, "rb") as img_file:
        img2_base64 = base64.b64encode(img_file.read()).decode("utf-8")

    with open(image3_path, "rb") as img_file:
        img3_base64 = base64.b64encode(img_file.read()).decode("utf-8")

    html(f"""
        <div style="width: 100%; overflow: hidden; padding: 10px 0; position: relative; background-color: #f5f5f5;">
          <div class="scroll-container" style="
              display: flex;
              width: fit-content;
              animation: scrollLoop 30s linear infinite;
          ">

            <!-- First track of images -->
            <div style="display: flex;">
              <img src="data:image/png;base64,{img1_base64}" style="width:400px; margin-right:30px; border-radius: 12px;" />
              <img src="data:image/png;base64,{img2_base64}" style="width:400px; margin-right:30px; border-radius: 12px;" />
              <img src="data:image/png;base64,{img3_base64}" style="width:400px; margin-right:30px; border-radius: 12px;" />
            </div>

            <!-- Duplicate track for seamless scrolling -->
            <div style="display: flex;">
              <img src="data:image/png;base64,{img1_base64}" style="width:400px; margin-right:30px; border-radius: 12px;" />
              <img src="data:image/png;base64,{img2_base64}" style="width:400px; margin-right:30px; border-radius: 12px;" />
              <img src="data:image/png;base64,{img3_base64}" style="width:400px; margin-right:30px; border-radius: 12px;" />
            </div>

          </div>
        </div>

        <style>
        @keyframes scrollLoop {{
  0% {{ transform: translateX(0); }}
  100% {{ transform: translateX(-50%); }}
}}
.scroll-container {{
  display: flex;
  animation: scrollLoop 30s linear infinite;
}}
        </style>
        """, height=300)

    add_vertical_space(2)

    st.header("Why TownSense?")

    col1,col2,col3 = st.columns([1,3,1])

    with col2:

        html("""
        <style>
        .grid-container {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 30px;
          margin-top: 40px;
          font-family: 'Trebuchet MS', sans-serif;
        }
    
        .grid-item {
          background-color: #f8f8f8;
          padding: 20px;
          border-radius: 12px;
          box-shadow: 0 4px 8px rgba(0, 0, 0, 0.06);
          opacity: 0;
          transform: translateY(30px);
          transition: opacity 0.8s ease 0.4s, transform 0.8s ease 0.4s;
        }
    
        .grid-item.visible {
          opacity: 1;
          transform: translateY(0);
        }
        </style>
    
        <div class="grid-container">
          <div class="grid-item">
            <h3>📸 Image Upload</h3>
            <p>Snap or upload a street photo and let TownSense analyze it for issues.</p>
          </div>
          <div class="grid-item">
            <h3>🧠 Smart Detection</h3>
            <p>Our AI pinpoints potholes, trash, graffiti, and more.</p>
          </div>
          <div class="grid-item">
            <h3>📍 Smart Reporting</h3>
            <p>Generate clean, structured reports for city services and civic dashboards.</p>
          </div>
          <div class="grid-item">
            <h3>🎯 Social Impact</h3>
            <p>Users earn points for relevant reports. Help improve your city in real time.</p>
          </div>
        </div>
    
        <script>
        const items = document.querySelectorAll('.grid-item');
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                }
            });
        }, { threshold: 0.1 });
    
        items.forEach(item => observer.observe(item));
        </script>
        """, height=500)

    col1, col2, col3 = st.columns([1, 5, 1])
    with col2:
        html("""
        <style>
            .cta-container {
            background-color: #000000;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-top: 30px;
            text-align: center;
            opacity: 0;
            font-family: 'Trebuchet MS', sans-serif;
            transform: translateY(30px);
            transition: opacity 0.8s ease 0.3s, transform 0.8s ease 0.3s;
        }

        .cta-container.visible {
            opacity: 1;
            transform: translateY(0);
        }
        </style>

        <div class="cta-container">
            <h2 style="color: #ffffff;">Ready to experience the future of urban issue detection?</h2>
            <p style="font-size: 18px; color: #ffffff;">
                Upload images and let our AI detect urban issues instantly!
            </p>
        </div>

        <script>
        const cta = document.querySelector('.cta-container');
        const observerCTA = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                }
            });
        }, { threshold: 0.1 });

        observerCTA.observe(cta);
        </script>
        """, height=280)

