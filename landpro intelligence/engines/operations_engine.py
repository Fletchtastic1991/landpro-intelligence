def estimate_operations(acres, vegetation, difficulty_score, config):

    base_productivity = config["productivity"][vegetation]

    if difficulty_score <= 30:
        difficulty_factor = 1.0
    elif difficulty_score <= 60:
        difficulty_factor = 0.75
    else:
        difficulty_factor = 0.5

    adjusted_productivity = base_productivity * difficulty_factor

    hours = acres / adjusted_productivity

    crew_size = config["crew_size"]
    hourly_rate = config["hourly_rate"]
    equipment_rate = config["equipment_rate"]

    labor_cost = hours * hourly_rate
    equipment_cost = hours * equipment_rate

    total_cost = labor_cost + equipment_cost

    return {
        "estimated_hours": round(hours, 2),
        "crew_size": crew_size,
        "labor_cost": round(labor_cost, 2),
        "equipment_cost": round(equipment_cost, 2),
        "total_operational_cost": round(total_cost, 2)
    }