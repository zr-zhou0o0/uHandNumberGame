import json

# 定义必输区域（三元组列表）
loss_states = [
    (2, 3, 5),
    (2, 5, 3),
    (4, 1, 5),
    (4, 5, 1),
    (6, 5, 9),
    (6, 9, 5),
    (8, 5, 7),
    (8, 7, 5)
]

# loss_states = [
#     (1, 7, 7),
#     (3, 1, 1),
#     (7, 9, 9),
#     (9, 3, 3),
# ]

# loss_states = [
#     (2, 3, 5),
#     (2, 5, 3),
#     (4, 1, 5),
#     (4, 5, 1),
#     (6, 5, 9),
#     (6, 9, 5),
#     (8, 5, 7),
#     (8, 7, 5),
#     (1, 7, 7),
#     (3, 1, 1),
#     (7, 9, 9),
#     (9, 3, 3),
# ]

# 存储符合条件的初始状态和对应的四种状态
results = {}

# 遍历所有可能的a、b、c（1到9）
for a in range(1, 10):
    for b in range(1, 10):
        for c in range(1, 10):
            # 计算四种状态（取模10）
            s1 = ((a + b) % 10, (a + 2 * b) % 10, c)
            s2 = ((a + b) % 10, b, (a + b + c) % 10)
            s3 = ((a + c) % 10, (a + b + c) % 10, c)
            s4 = ((a + c) % 10, b, (a + 2 * c) % 10)
            
            # 检查所有四种状态是否都在必输区域中
            # 三个不在其实也不能百分百胜利，因为剩下两个怎么选，是由对手决定的。
            # if s1 in loss_states and s2 in loss_states and s3 in loss_states and s4 in loss_states:
            #     key = f"[{a}, {b}, {c}]"
            #     value = {
            #         "state1": list(s1),
            #         "state2": list(s2),
            #         "state3": list(s3),
            #         "state4": list(s4)
            #     }
            #     results[key] = value

            if (s1 not in loss_states and s2 not in loss_states) or (s3 not in loss_states and s4 not in loss_states):
                continue
            else:
                key = f"[{a}, {b}, {c}]"
                value = {
                    "state1": list(s1),
                    "state2": list(s2),
                    "state3": list(s3),
                    "state4": list(s4)
                }
                results[key] = value

# 保存结果到JSON文件
# with open(r'scripts\game\four_step_enum.json', 'w') as f:
with open(r'scripts\game\two_step_enum.json', 'w') as f:
    json.dump(results, f, indent=4)

print("符合条件的初始状态已保存")