import json

memo = {}

def solve(a, b, turn):
    state = (a, b, turn)
    if state in memo:
        if memo[state] is None:
            return 0.5
        return memo[state]
    
    memo[state] = None
    
    if turn == 'me':
        new_a = (a + b) % 10
        if new_a == 0:
            result = 1
        else:
            next_result = solve(new_a, b, 'opponent')
            result = next_result
    else:
        new_b = (b + a) % 10
        if new_b == 0:
            result = 0
        else:
            next_result = solve(a, new_b, 'me')
            result = next_result
            
    memo[state] = result
    return result

result_dict = {}
for a in range(1, 10):
    for b in range(1, 10):
        outcome = solve(a, b, 'me')
        result_dict[f"[{a}, {b}]"] = outcome

# 将字典保存为JSON文件
with open(r'scripts\game\one_one_enum.json', 'w') as f:
    json.dump(result_dict, f, indent=4)

print("结果已保存到 game_results.json 文件中")