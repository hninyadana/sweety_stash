import streamlit as st
import json
import os
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px

# --- CONFIGURATION & DATA PERSISTENCE ---
# Use a relative path for the data file.
DATA_FILE = "sweety_stash_data.json"
PET_NAME_DEFAULT = "Sweety"
EXPENSE_CATEGORIES = [
    "Food", "Transport", "Shopping", "Entertainment", "Utilities", "Other"
]

# Set page configuration for a clean, wide layout
st.set_page_config(page_title="Sweety Stash",
                   page_icon="😻",
                   layout="wide",
                   initial_sidebar_state="expanded")

# --- UTILITY FUNCTIONS ---


def _load_data():
    """Loads application data from the JSON file."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, Exception):
            # If load fails, return empty dict to start fresh
            return {}
    return {}


def _save_data(data):
    """Saves application data to the JSON file."""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception:
        # Streamlit will handle errors more gracefully than just printing
        st.error("Could not save data. Check file permissions.")
        return False


def _initialize_defaults():
    """Initializes default values and loads data into session state."""
    if 'app_data' not in st.session_state:
        data = _load_data()

        data.setdefault("monthly_income", 0.0)
        data.setdefault("monthly_savings_goal", 0.0)
        data.setdefault("fixed_expenses", {})
        data.setdefault("daily_expenses", [])
        data.setdefault("extra_goals", {})
        data.setdefault("pet_name", PET_NAME_DEFAULT)
        data.setdefault("saving_streak", 0)
        data.setdefault("last_streak_date", None)
        data.setdefault("daily_treat_given", False)
        data.setdefault("last_treat_date", None)
        data.setdefault("rewards_unlocked", [])

        st.session_state.app_data = data
        _save_data(data)


# --- CORE LOGIC FUNCTIONS ---


def get_financial_summary(data):
    """Calculates all key financial metrics."""
    income = data["monthly_income"]
    fixed = sum(data["fixed_expenses"].values())
    goal = data["monthly_savings_goal"]

    today = datetime.now().strftime("%Y-%m-%d")
    current_month = datetime.now().strftime("%Y-%m")

    # Use a DataFrame for efficient calculations
    df = pd.DataFrame(data["daily_expenses"])

    if df.empty:
        total_spent = 0.0
        todays_spent = 0.0
    else:
        df['date_obj'] = pd.to_datetime(df['date'])

        # Expenses this month (excluding big purchases)
        expenses_this_month = df[df['date_obj'].dt.strftime('%Y-%m') ==
                                 current_month]
        total_spent = expenses_this_month[
            ~expenses_this_month['is_big_purchase']]['amount'].sum()

        # Spent today (excluding big purchases)
        todays_expenses = df[df['date'] == today]
        todays_spent = todays_expenses[~todays_expenses['is_big_purchase']][
            'amount'].sum()

    # Remaining days calculation
    now = datetime.now()
    # Find the last day of the current month
    next_month = now.replace(day=28) + timedelta(days=4)
    last_day = next_month - timedelta(days=next_month.day)
    remaining_days = max(1, (last_day - now).days +
                         1)  # Ensure at least 1 day remaining

    disposable = income - fixed - goal
    # Daily allowance is only distributed if disposable income is positive
    daily_allowance = max(0, disposable /
                          remaining_days) if remaining_days > 0 else 0

    todays_savings = daily_allowance - todays_spent
    daily_used_percent = min(100, (todays_spent / daily_allowance) *
                             100) if daily_allowance > 0 else 0

    return {
        "monthly_income": income,
        "fixed_expenses_sum": fixed,
        "target_saving": goal,
        "daily_allowance": daily_allowance,
        "todays_expenses": todays_spent,
        "todays_savings": todays_savings,
        "total_spent_month": total_spent,
        "daily_used_percent": daily_used_percent,
        "remaining_days": remaining_days
    }


def get_pet_status(data, financials):
    """Determines the pet's mood, message, and image."""
    savings = financials["todays_savings"]
    treat = data["daily_treat_given"]

    mood, image, msg = "Neutral", "🐱", "Waiting for updates..."

    if financials["monthly_income"] == 0:
        msg = "Please set up your budget first in the sidebar!"
    elif savings >= 0 and financials["todays_expenses"] > 0:
        mood, image, msg = "Happy", "😺", "Purrfect! On track today."
    elif savings < 0:
        mood, image, msg = "Sad", "😿", "Careful! You've gone over budget."

    if treat:
        mood, image, msg = "Excited", "😻", f"Yum! Treats make {data['pet_name']} happy! Keep saving!"

    return {
        "mood": mood,
        "message": msg,
        "image": image,
        "streak": data["saving_streak"]
    }


def check_daily_reset(data):
    """Resets daily treat status and saves the updated state."""
    today = datetime.now().strftime("%Y-%m-%d")
    if data.get("last_treat_date") != today:
        data["daily_treat_given"] = False
        data["last_treat_date"] = today
        return True
    return False


def update_streak(data, todays_savings):
    """Updates the saving streak based on today's surplus."""
    today = datetime.now().strftime("%Y-%m-%d")
    streak = data["saving_streak"]
    last = data["last_streak_date"]

    if todays_savings >= 0:
        if last != today:
            if last:
                # Check if it's the day immediately following the last streak day
                last_dt = datetime.strptime(last, "%Y-%m-%d")
                if (datetime.now().date() - last_dt.date()).days == 1:
                    data["saving_streak"] += 1
                elif (datetime.now().date() - last_dt.date()).days > 1:
                    data["saving_streak"] = 1  # Streak broken, restart
            else:
                data["saving_streak"] = 1  # Start new streak
            data["last_streak_date"] = today
    else:
        # Saving is negative, streak is broken
        data["saving_streak"] = 0
        data[
            "last_streak_date"] = today  # Reset last streak date to today to prevent immediate re-breaking on refresh

    return data["saving_streak"]


def check_rewards(data):
    """Checks for and unlocks new rewards."""
    streak = data["saving_streak"]
    rewards = data["rewards_unlocked"]
    new_reward = None

    if streak >= 7 and "Weekly Spa" not in rewards:
        rewards.append("Weekly Spa")
        new_reward = "Weekly Spa"
    if streak >= 30 and "Monthly Vacation" not in rewards:
        rewards.append("Monthly Vacation")
        new_reward = "Monthly Vacation"

    data["rewards_unlocked"] = rewards
    return new_reward


# --- CALLBACK FUNCTIONS FOR FORMS ---


def log_expense_callback(amount, category, description, is_big_purchase):
    """Handles logging an expense and updating the streak."""
    data = st.session_state.app_data

    if amount <= 0:
        st.error("Expense amount must be positive.")
        return

    transaction = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "amount": float(amount),
        "category": category,
        "description": description,
        "is_big_purchase": is_big_purchase
    }
    data["daily_expenses"].append(transaction)

    # Recalculate financial summary to get new savings value for streak update
    financials = get_financial_summary(data)
    update_streak(data, financials["todays_savings"])
    new_reward = check_rewards(data)

    _save_data(data)

    st.session_state.app_data = data
    st.toast("Expense logged successfully!")
    if new_reward:
        st.balloons()
        st.toast(f"🎉 New Reward Unlocked: {new_reward}! 🎉", icon="🎁")


def update_budget_callback(income, goal, fixed_expenses):
    """Handles updating the main budget settings."""
    data = st.session_state.app_data

    if income < 0 or goal < 0:
        st.error("Income and savings goal cannot be negative.")
        return

    if sum(fixed_expenses.values()) > income:
        st.error("Total fixed expenses exceed your monthly income!")
        return

    data["monthly_income"] = income
    data["monthly_savings_goal"] = goal
    data["fixed_expenses"] = fixed_expenses

    _save_data(data)
    st.session_state.app_data = data
    st.toast("Budget updated successfully!", icon="📝")


def give_treat_callback():
    """Handles giving the pet a treat."""
    data = st.session_state.app_data
    if data["daily_treat_given"]:
        st.error(f"{data['pet_name']} already got a treat today!")
        return

    financials = get_financial_summary(data)

    if financials["todays_savings"] >= 0:
        data["daily_treat_given"] = True
        data["last_treat_date"] = datetime.now().strftime("%Y-%m-%d")
        _save_data(data)
        st.session_state.app_data = data
        st.toast(f"You gave {data['pet_name']} a treat! 😻", icon="🦴")
    else:
        st.error(
            f"You need to be on budget (or below) to give {data['pet_name']} a treat!"
        )


# --- VISUALIZATION ---


def generate_spending_chart(daily_expenses):
    """Generates a pie chart of spending by category for the current month."""
    if not daily_expenses:
        return None

    df = pd.DataFrame(daily_expenses)
    df['date_obj'] = pd.to_datetime(df['date'])
    current_month = datetime.now().strftime("%Y-%m")

    df_current_month = df[df['date_obj'].dt.strftime('%Y-%m') == current_month]

    # Group by category, excluding big purchases for the main pie chart
    df_grouped = df_current_month[
        ~df_current_month['is_big_purchase']].groupby(
            'category')['amount'].sum().reset_index()

    if df_grouped.empty:
        return None

    fig = px.pie(
        df_grouped,
        values='amount',
        names='category',
        title='Monthly Spending Breakdown (Excluding Fixed & Big Purchases)',
        hole=0.3,
        color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(showlegend=False, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def generate_extra_goals_chart(extra_goals):
    """Generates a bar chart showing progress toward extra goals."""
    if not extra_goals:
        return None

    goals_list = []
    for name, data in extra_goals.items():
        # Use .get() with default values to prevent KeyError if the data structure is inconsistent.
        current_saved = data.get('current', 0.0)
        target = data.get('target', 0.0)

        # Prevent division by zero
        progress = (current_saved / target) * 100 if target > 0 else 0

        goals_list.append({
            'Goal': name,
            'Current': current_saved,
            'Target': target,
            'Progress': progress
        })

    df_goals = pd.DataFrame(goals_list)
    # Filter out goals where both current and target are zero, which don't make sense to plot.
    df_goals = df_goals[(df_goals['Current'] > 0) | (df_goals['Target'] > 0)]

    if df_goals.empty:
        return None

    fig = px.bar(df_goals,
                 x='Goal',
                 y='Target',
                 title='Extra Savings Goal Progress',
                 color_discrete_sequence=['rgb(171, 99, 230)'])
    # Add a progress bar overlay
    fig.add_bar(x=df_goals['Goal'],
                y=df_goals['Current'],
                name='Current Progress',
                marker_color='rgb(102, 194, 165)')

    fig.update_traces(texttemplate='%{y:$.2f}', textposition='outside')
    fig.update_layout(barmode='overlay', xaxis_tickangle=-45, showlegend=False)
    # Ensure y-axis range is appropriate
    y_max = df_goals['Target'].max()
    fig.update_yaxes(title_text="Amount (USD)",
                     range=[0, y_max * 1.1 if y_max > 0 else 100])
    return fig


# --- MAIN APPLICATION LAYOUT ---


def main():
    """The main Streamlit application function."""
    _initialize_defaults()
    data = st.session_state.app_data

    # Check for daily reset and update data if necessary
    if check_daily_reset(data):
        _save_data(data)
        st.session_state.app_data = data  # Update session state after save

    financials = get_financial_summary(data)
    pet_status = get_pet_status(data, financials)

    # Run streak check again in main loop to catch today's new logs
    update_streak(data, financials["todays_savings"])
    check_rewards(data)  # Check rewards after streak update
    _save_data(data)  # Save state after streak/reward check

    st.title(f"{pet_status['image']} {data['pet_name']}'s Stash")

    # ----------------------------------
    # 1. PET STATUS & DAILY SUMMARY
    # ----------------------------------
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Daily Allowance",
                  value=f"${financials['daily_allowance']:.2f}")

    with col2:
        st.metric(label="Remaining Budget Today",
                  value=f"${financials['todays_savings']:.2f}",
                  delta=f"${financials['todays_expenses']:.2f} spent"
                  if financials['todays_expenses'] > 0 else "No spending yet")

    with col3:
        st.metric(label="Current Saving Streak",
                  value=f"{data['saving_streak']} days",
                  help="Streak increases every day you stay within budget.")

    st.subheader(f"Pet Status: {pet_status['mood']} - {pet_status['message']}")

    # Daily spending progress bar
    progress_text = f"Daily Budget Used: {financials['daily_used_percent']:.1f}%"
    st.progress(financials['daily_used_percent'] / 100, text=progress_text)

    st.button(f"Give {data['pet_name']} a Treat (Only if on Budget!)",
              on_click=give_treat_callback,
              disabled=data['daily_treat_given'])

    st.divider()

    # ----------------------------------
    # 2. LOG EXPENSE FORM
    # ----------------------------------
    with st.expander("💸 Log a New Expense"):
        expense_amount = st.number_input("Amount (USD)",
                                         min_value=0.01,
                                         format="%.2f",
                                         key="expense_amount")
        expense_category = st.selectbox("Category",
                                        EXPENSE_CATEGORIES,
                                        key="expense_category")
        expense_description = st.text_input("Description (optional)",
                                            key="expense_description")
        is_big_purchase = st.checkbox(
            "Is this a one-off Big Purchase (e.g., new laptop)?",
            key="is_big_purchase")

        st.button("Log Expense",
                  on_click=log_expense_callback,
                  args=[
                      expense_amount, expense_category, expense_description,
                      is_big_purchase
                  ])

    st.divider()

    # ----------------------------------
    # 3. CHARTS & GOALS
    # ----------------------------------
    st.header("Financial Overview")

    tab1, tab2, tab3 = st.tabs(
        ["Monthly Spending", "Savings Goals", "Rewards"])

    with tab1:
        st.subheader("Current Month's Spending")
        chart = generate_spending_chart(data['daily_expenses'])
        if chart:
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.info("No daily expenses logged for this month yet.")

        st.subheader("Monthly Financial Breakdown")
        st.dataframe(
            pd.DataFrame({
                'Metric': [
                    'Monthly Income', 'Fixed Expenses', 'Monthly Savings Goal',
                    'Disposable Income'
                ],
                'Amount (USD)': [
                    financials['monthly_income'],
                    financials['fixed_expenses_sum'],
                    financials['target_saving'], financials['monthly_income'] -
                    financials['fixed_expenses_sum'] -
                    financials['target_saving']
                ]
            }))

    with tab2:
        st.subheader("Extra Savings Goal Progress")
        goals_chart = generate_extra_goals_chart(data['extra_goals'])
        if goals_chart:
            st.plotly_chart(goals_chart, use_container_width=True)
        else:
            st.info("No extra savings goals have been set yet.")

        # Form to add/update extra goals
        with st.expander("➕ Manage Extra Goals"):
            goal_name = st.text_input(
                "Goal Name (e.g., Vacation, Laptop Fund)",
                key="goal_name_input")
            goal_target = st.number_input("Target Amount (USD)",
                                          min_value=0.0,
                                          format="%.2f",
                                          key="goal_target_input")
            current_saved = st.number_input("Current Saved Amount (USD)",
                                            min_value=0.0,
                                            format="%.2f",
                                            key="goal_current_input")

            if st.button("Save/Update Goal", key="save_goal_button"):
                if goal_name and goal_target > 0:
                    data['extra_goals'][goal_name] = {
                        'target': goal_target,
                        'current': current_saved
                    }
                    _save_data(data)
                    st.session_state.app_data = data
                    st.toast(f"Goal '{goal_name}' updated!")
                    st.rerun()
                else:
                    st.error("Goal Name and Target Amount are required.")

    with tab3:
        st.subheader("Unlocked Rewards")
        if data['rewards_unlocked']:
            for reward in data['rewards_unlocked']:
                st.success(f"🎁 {reward}")
        else:
            st.info("No rewards unlocked yet. Keep your streak alive!")

    # ----------------------------------
    # 4. SIDEBAR SETTINGS (BUDGET)
    # ----------------------------------
    with st.sidebar:
        st.title("⚙️ Budget Settings")

        # Pet Name Change
        new_pet_name = st.text_input("Change Pet's Name:",
                                     value=data["pet_name"],
                                     key="pet_name_input")
        if new_pet_name and new_pet_name != data["pet_name"]:
            data["pet_name"] = new_pet_name
            _save_data(data)
            st.session_state.app_data = data
            st.rerun()  # Rerun to update title immediately

        # Budget Input Form
        with st.form("budget_form"):
            st.subheader("Income & Savings")

            # Use data from session state as default values
            monthly_income = st.number_input("Monthly Income (USD)",
                                             min_value=0.0,
                                             value=data["monthly_income"],
                                             format="%.2f",
                                             key="inc_input")
            monthly_savings_goal = st.number_input(
                "Monthly Savings Goal (USD)",
                min_value=0.0,
                value=data["monthly_savings_goal"],
                format="%.2f",
                key="goal_input")

            st.subheader("Fixed Expenses")

            # Dynamic Fixed Expense Inputs
            fixed_expenses_inputs = {}
            default_fixed = data["fixed_expenses"]

            # List known categories
            known_fixed_categories = list(default_fixed.keys())

            for category in known_fixed_categories:
                fixed_expenses_inputs[category] = st.number_input(
                    f"{category} (USD)",
                    min_value=0.0,
                    value=default_fixed.get(category, 0.0),
                    format="%.2f",
                    key=f"fixed_{category}")

            new_fixed_category = st.text_input("New Fixed Expense Name",
                                               key="new_fixed_category_name")
            if new_fixed_category:
                fixed_expenses_inputs[new_fixed_category] = st.number_input(
                    f"{new_fixed_category} (USD)",
                    min_value=0.0,
                    value=0.0,
                    format="%.2f",
                    key=f"fixed_new_{new_fixed_category}")

            submitted = st.form_submit_button("Update Budget")

            if submitted:
                # Filter out zero/empty values and non-numeric entries
                valid_fixed = {
                    k: v
                    for k, v in fixed_expenses_inputs.items() if v > 0
                }

                update_budget_callback(income=monthly_income,
                                       goal=monthly_savings_goal,
                                       fixed_expenses=valid_fixed)
                st.rerun()  # Rerun to refresh the main page metrics


if __name__ == "__main__":
    main()
