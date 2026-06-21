def check_plant_status(soil, temperature, humidity, light):
    status_list = []
    status_icon_list = []
    action_list = []
    problem_count = 0

    if soil < 30:
        status_list.append("토양 수분 부족")
        action_list.append({"icon": "droplets", "text": "물 좀 주세요"})
        problem_count += 1
    elif soil > 70:
        status_list.append("토양 수분 과다")
        action_list.append({"icon": "droplets", "text": "잠시 물 주기를 멈춰주세요"})
        problem_count += 1
    else:
        status_list.append("토양 수분 적정")
        action_list.append({"icon": "heart", "text": "아주 적당히 촉촉해요!"})

    if temperature < 18:
        status_list.append("온도 낮음")
        action_list.append({"icon": "thermometer", "text": "조금 더 따뜻한 곳으로 옮겨주세요"})
        problem_count += 1
    elif temperature > 30:
        status_list.append("온도 높음")
        action_list.append({"icon": "thermometer", "text": "직사광선이나 더운 곳을 피해주세요"})
        problem_count += 1
    else:
        status_list.append("온도 적정")
        action_list.append({"icon": "heart", "text": "온도가 적정해요!"})

    if humidity < 40:
        status_list.append("습도 낮음")
        action_list.append({"icon": "leaf", "text": "주변 습도를 조금 높여주세요"})
        problem_count += 1
    elif humidity > 80:
        status_list.append("습도 높음")
        action_list.append({"icon": "wind", "text": "환기가 필요해요"})
        problem_count += 1
    else:
        status_list.append("습도 적정")
        action_list.append({"icon": "heart", "text": "공기가 쾌적해요!"})

    if light < 300:
        status_list.append("조도 부족")
        action_list.append({"icon": "sun", "text": "밝은 곳으로 이동하면 좋아요"})
        problem_count += 1
    elif light > 900:
        status_list.append("조도 강함")
        action_list.append({"icon": "sun", "text": "빛이 너무 강하지 않은 곳이 좋아요"})
        problem_count += 1
    else:
        status_list.append("조도 적정")
        action_list.append({"icon": "heart", "text": "햇살이 따스해서 기분이 좋아요!"})

    if problem_count >= 3:
        mood = "아파요"
        mood_class = "danger"
        image = "basil_emergency.png"
        message = "저를 보살펴 주세요..."

    elif "토양 수분 부족" in status_list:
        mood = "목말라요"
        mood_class = "thirsty"
        image = "basil_thirsty.png"
        message = "물 좀 주세요!"

    elif "토양 수분 과다" in status_list:
        mood = "축축해요"
        mood_class = "thirsty"
        image = "basil_overwatered.png"
        message = "축축해서 기분이 쳐져요. 잠깐 쉬고 싶어요."

    elif "조도 부족" in status_list:
        mood = "졸려요"
        mood_class = "sleepy"
        image = "basil_sunlight.png"
        message = "햇빛 좀 쬐고 싶어요."

    elif "온도 높음" in status_list:
        mood = "더워요"
        mood_class = "hot"
        image = "basil_hot.png"
        message = "조금 더워요. 시원하게 해주세요."

    elif "온도 낮음" in status_list:
        mood = "추워요"
        mood_class = "cold"
        image = "basil_cold.png"
        message = "몸이 으슬으슬해요. 따뜻하게 해주세요."

    elif "습도 낮음" in status_list:
        mood = "건조해요"
        mood_class = "thirsty"
        image = "basil_thirsty.png"
        message = "목이 건조해요. 촉촉하면 좋겠어요."

    else:
        mood = "행복해요"
        mood_class = "happy"
        image = "basil_happy.png"
        message = "모든 게 완벽해서 기분이 좋아요!"

    if "조도 부족" in status_list:
        action = "move_to_light"
        action_message = {"icon": "sun", "text": "밝은 곳 탐색 중"}
    elif "토양 수분 부족" in status_list:
        action = "need_water"
        action_message = {"icon": "droplets", "text": "물 필요"}
    elif "온도 높음" in status_list:
        action = "avoid_heat"
        action_message = {"icon": "thermometer", "text": "더위 피하는 중"}
    elif "온도 낮음" in status_list:
        action = "find_warm_place"
        action_message = {"icon": "flame", "text": "따뜻한 곳 필요"}
    else:
        action = "idle"
        action_message = {"icon": "leaf", "text": "현재 위치 유지"}

    return {
        "status_list": status_list,
        "status_icon_list": status_icon_list,
        "action_list": action_list,
        "mood": mood,
        "mood_class": mood_class,
        "image": image,
        "message": message,
        "action": action,
        "action_message": action_message
    }