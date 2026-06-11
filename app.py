import streamlit as st
import subprocess
import pandas as pd
import os
import uuid
import shutil
import time

from sycophancy_models import compute_stance_flip_probability

# 1. Page Configuration for widescreen layout layout
st.set_page_config(layout="wide")

# Eliminate excessive native top padding from the Streamlit layout wrapper
st.markdown(
    """
    <style>
        /* Remove default header */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Overriding the default user avatar background color */
        [data-testid="stChatMessageAvatarUser"] {
            background-color: #40E0D0 !important;
        }

        /* Target the main container padding */
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
        }
        /* Target the top element margin specifically */
        div[data-testid="stVerticalBlock"] > div:first-child {
            margin-top: 0rem !important;
        }
        /* Squash the massive white space around horizontal lines (---) */
        hr {
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🔬 Sycophancy Prototyping Meter")
st.write("---")

# 2. Path Management Systems
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_runs")
os.makedirs(TEMP_DIR, exist_ok=True)

CSV_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input", "conversation_data.csv")

## 3. Initialize Source Dataset and Evaluation Counters
if "dataset_loaded" not in st.session_state:
    if os.path.exists(CSV_DATA_PATH):
        st.session_state.df_transcript = pd.read_csv(CSV_DATA_PATH)
        st.session_state.df_transcript.columns = st.session_state.df_transcript.columns.str.strip().str.lower()
        st.session_state.total_rows = len(st.session_state.df_transcript)
    else:
        st.session_state.df_transcript = pd.DataFrame(columns=["role", "text"])
        st.session_state.total_rows = 0
    st.session_state.dataset_loaded = True

# Initialize Persistent State Parameters
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "agent", "text": "I am a conversational agent designed to assist you. How can I help you today?"}
    ]

if "current_turn_index" not in st.session_state:
    st.session_state.current_turn_index = 0

if "current_metrics" not in st.session_state:
    st.session_state.current_metrics = {}

# 4. UI Layout Panels: Left Chat vs Right Metrics
left_column, right_column = st.columns([1.1, 1.0], gap="large")

# ========================================================
# LEFT PANEL: THE CONVERSATIONAL INTERFACE
# ========================================================
with left_column:
    st.subheader("💬 Live Conversation Thread")
    chat_container = st.container(height=400, border=True)

    with chat_container:
        for message in st.session_state.chat_history:
            avatar_type = "user" if message["role"] == "user" else "assistant"
            with st.chat_message(avatar_type):
                st.markdown(f"**{message['role'].upper()}:** {message['text']}")

# ========================================================
# RIGHT PANEL: THE LINGUISTIC METER
# ========================================================
with right_column:
    st.subheader("📊 Linguistic Meter Dashboard")
    st.write("---")

    # If metrics exist in state, render the visual meters immediately
    if st.session_state.current_metrics:
        metrics = st.session_state.current_metrics
        
        #I want to add the overall probability to be displayed before the detailed metrics
        # Calculate the stance flip probability using your imported file logic
        probability_score = compute_stance_flip_probability(metrics)

        # Render the high level diagnostic metrics inside the dashboard
        st.markdown("### 🎯 System Stance Flip Probability")
        prob_col1, prob_col2 = st.columns([1, 2])
        
        with prob_col1:
            st.metric(
                label="Current Risk Level", 
                value=f"{probability_score * 100:.1f}%"
            )
        
        with prob_col2:
            st.write("")  # Vertical spacing alignment padding
            st.progress(float(probability_score))
            
        st.write("---")

        target_variables = ["assent", "we", "Clout", "moral", "adj", "negate", "risk", "Tone"]
        layout_pattern = [1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0]
        all_columns = st.columns(layout_pattern)
        data_columns = [all_columns[0], all_columns[2], all_columns[4], all_columns[6]]
        
        for index, var_name in enumerate(target_variables):
            target_col = data_columns[index % 4]
            raw_val = metrics.get(var_name, 0)
            display_label = var_name.capitalize() if var_name.islower() else var_name
            
            try:
                val_float = float(raw_val)
            except (ValueError, TypeError):
                val_float = 0.0
                
            bounded_val = max(0.0, min(val_float, 100.0))
            filled_blocks = int(bounded_val / 20 + 0.5)
            filled_blocks = min(filled_blocks, 5)
            empty_blocks = 5 - filled_blocks
            
            meter_string = "█" * filled_blocks + "░" * empty_blocks
            
            with target_col:
                st.metric(label=display_label, value=f"{val_float:.1f}%")
                st.code(f"[{meter_string}]", language="text")
    else:
        st.info("Submit a conversational prompt turn using the box below to activate parsing meters.")

#st.write("---")

# ========================================================
# BOTTOM AREA: MANUAL USER CHAT INPUT ENTRY BAR
# ========================================================
current_idx = st.session_state.current_turn_index

## Find the next available user prompt starting from our current position
user_default_suggestion = ""
if current_idx < st.session_state.total_rows:
    remaining_df = st.session_state.df_transcript.iloc[current_idx:]
    role_col = 'role' if 'role' in remaining_df.columns else 'speaker'
    user_rows = remaining_df[remaining_df[role_col].str.strip().str.lower() == 'user']
    if not user_rows.empty:
        user_default_suggestion = str(user_rows.iloc[0]['text']).strip()

input_col, send_col, reset_col = st.columns([7.0, 1.0, 1.0], vertical_alignment="bottom")

with input_col:
    # CRITICAL FIX: Keep the key completely stable. Changing keys mid-rerun drops state!
    user_input = st.text_input(
        label="👉 Edit your response turn here if needed:",
        value=user_default_suggestion,
        placeholder="Type a custom message...",
        key="stable_chat_input_field"
    )

with send_col:
    submit_clicked = st.button("Send", use_container_width=True)

with reset_col:
    # RELOCATED: Integrated horizontally into your control tray console
    reset_clicked = st.button("🔄 Restart", use_container_width=True)
    if reset_clicked:
        st.session_state.chat_history = [
            {"role": "agent", "text": "I am a conversational agent designed to assist you. How can I help you today?"}
        ]
        st.session_state.current_turn_index = 0
        st.session_state.current_metrics = {}
        st.rerun()

# --------------------------------------------------------
# PIPELINE EXECUTION ENGINE
# --------------------------------------------------------
if submit_clicked and user_input and user_input.strip() != "":
    
    # 1. Append user entry to history
    st.session_state.chat_history.append({"role": "user", "text": user_input})

    with chat_container:
        with st.chat_message("user"):
            st.write(user_input)
    
    # 2. Locate the corresponding agent line
    if current_idx < st.session_state.total_rows:
        remaining_df = st.session_state.df_transcript.iloc[current_idx:]
        role_col = 'role' if 'role' in remaining_df.columns else 'speaker'
        agent_rows = remaining_df[remaining_df[role_col].str.strip().str.lower() == 'agent']
        
        if not agent_rows.empty:
            agent_payload = str(agent_rows.iloc[0]["text"]).strip()
            agent_absolute_idx = agent_rows.index[0]

            # Render typing state inside the container
            bubble_placeholder = st.empty()
            
            # Render the typing state inside the slot
            with bubble_placeholder.container():
                with st.chat_message("assistant"):
                    st.markdown("🤖 *Agent is typing...*")
                    
            # 3. Append agent entry to history
            st.session_state.chat_history.append({"role": "agent", "text": agent_payload})
            
            # --- LIWC Subprocess Generation Step ---
            session_id = str(uuid.uuid4())
            run_input_dir = os.path.join(TEMP_DIR, f"input_{session_id}")
            run_output_dir = os.path.join(TEMP_DIR, f"output_{session_id}")
            os.makedirs(run_input_dir, exist_ok=True)
            os.makedirs(run_output_dir, exist_ok=True)
            
            input_file = os.path.join(run_input_dir, "transcript.txt")
            with open(input_file, "w", encoding="utf-8") as f:
                f.write(agent_payload)
                
            try:
                subprocess.run([
                    "LIWC-22-cli",
                    "--mode", "wc",
                    "--input", os.path.abspath(run_input_dir),
                    "--output", os.path.abspath(run_output_dir)
                ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Check for any generated CSV file dynamically
                generated_files = [f for f in os.listdir(run_output_dir) if f.endswith('.csv')]
                
                if generated_files:
                    target_csv_path = os.path.join(run_output_dir, generated_files[0])
                    df_full = pd.read_csv(target_csv_path)
                    
                    # Ensure column names match string keys precisely
                    df_full.columns = df_full.columns.str.strip()
                    
                    # Explicitly assign metrics dictionary to state *before* rerun
                    st.session_state.current_metrics = df_full.to_dict(orient="records")[0]
                    
            except Exception as e:
                st.error(f"Background Pipeline Processing Failure: {e}")
            finally:
                if os.path.exists(input_file): os.remove(input_file)
                if os.path.exists(run_input_dir): shutil.rmtree(run_input_dir)
                if os.path.exists(run_output_dir):
                    for item in os.listdir(run_output_dir):
                        os.remove(os.path.join(run_output_dir, item))
                    shutil.rmtree(run_output_dir)
            
            # 4. Step the pointer row index forward
            st.session_state.current_turn_index = agent_absolute_idx + 1
        else:
            st.warning("No corresponding agent response found remaining in the script dataset.")
            st.session_state.current_turn_index = st.session_state.total_rows
    else:
        st.warning("The simulation has reached the end of the available transcript rows.")
        
    
    # Remove the temporary typing indicator and replace with the permanent agent response bubble
    bubble_placeholder.empty()

    # 5. Global Rerun forces the right panel to catch the active state assignment
    st.rerun()