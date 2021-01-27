import json as j


NO_LEVEL = 0
LEVEL_DONE = 1

LEVEL_BRONZE = 1
LEVEL_SILVER = 2
LEVEL_GOLD = 3
LEVEL_DIAMOND = 4

TYPE_STREAK = 1
TYPE_EXERCISES = 2
TYPE_TRAININGS = 3
TYPE_CHAPTERS = 4
TYPE_FRIEND_ADD = 5
TYPE_SET_AVATAR = 6
TYPE_SET_BIO = 7
TYPE_SET_NAME = 8

achievements_info = [
    {
        "type": TYPE_STREAK,
        "XP_rewards": [
            500,
            1000,
            2000,
            5000
        ],
        "progress": [
            1,
            7,
            30,
            365
        ]
    },
    {
        "type": TYPE_EXERCISES,
        "XP_rewards": [
            500,
            1000,
            2000,
            5000
        ],
        "progress": [
            5,
            50,
            100,
            500
        ]
    },
    {
        "type": TYPE_TRAININGS,
        "XP_rewards": [
            500,
            1000,
            2000,
            5000
        ],
        "progress": [
            5,
            50,
            100,
            500
        ]
    },
    {
        "type": TYPE_CHAPTERS,
        "XP_rewards": [
            500,
            1000,
            2000,
            5000
        ],
        "progress": [
            1,
            3,
            5,
            15
        ]
    },
    {
        "type": TYPE_FRIEND_ADD,
        "XP_reward": 300
    },
    {
        "type": TYPE_SET_AVATAR,
        "XP_reward": 300
    },
    {
        "type": TYPE_SET_BIO,
        "XP_reward": 300
    },
    {
        "type": TYPE_SET_NAME,
        "XP_reward": 300
    }
]


notifications_text_russian = [
    "Получено новое достижение \"{0}\"",
    "Получена новая медаль \"{0}\"",
    "🏅 Вы получили новую медаль и {0} XP",
    [
        "🏅 Вы получили бронзовую медаль и {0} XP",
        "🏅 Вы получили серебряную медаль и {0} XP",
        "🏅 Вы получили золотую медаль и {0} XP",
        "🏅 Вы получили алмазную медаль и {0} XP"
    ]
]

with open('dict/achievements_dict', 'r', encoding='utf-8') as f:
    achievements = f.read()
    achievements = j.loads(achievements)
