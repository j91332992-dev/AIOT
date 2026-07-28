const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "Content-Type, X-OpenAI-Key",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

const mealSlots = ["morning", "lunch", "evening"] as const;
type MealSlot = (typeof mealSlots)[number];

type ChatMessage = {
  role?: "user" | "assistant";
  content?: string;
};

type AssistantPayload = {
  message?: string;
  history?: ChatMessage[];
  localDate?: string;
  context?: {
    connected?: boolean;
    timeSynced?: boolean;
    currentTime?: string;
    neopixel?: boolean;
    lightColor?: string;
    lightBrightness?: number;
    currentAngle?: number;
    pendingDoses?: number;
    activeSlot?: string;
    taken?: Record<string, boolean>;
    modelUrlConfigured?: boolean;
    recentEvents?: Array<{
      type?: string;
      mealSlot?: string | null;
      message?: string;
      time?: string | null;
    }>;
  };
};

type ModelAnswer = {
  reply: string;
  actionType: "none" | "record_manual_dose";
  mealSlot: "" | MealSlot;
  date: string;
  confirmationText: string;
};

type OpenAIResponse = {
  output?: Array<{
    type?: string;
    content?: Array<{ type?: string; text?: string }>;
  }>;
  error?: { message?: string };
};

const SYSTEM_INSTRUCTIONS = `
당신은 스마트 알약 디스펜서 앱 "Pillume"의 한국어 AI 챗봇이다.
사용자의 오타, 줄임말, 자연스러운 표현을 이해하고 친절하고 간결하게 답한다.

[앱 지식]
- ESP32 BLE 이름은 ESP_SZ이며 Wi-Fi 대신 Web Bluetooth로 연결한다.
- Chrome/Edge의 HTTPS 또는 localhost에서 BLE와 카메라가 동작한다.
- 복약 시간: 아침 07:00~10:00, 점심 11:00~13:00, 저녁 15:00~17:00.
- IR 센서에 손이 1초 연속 감지되면 약이 배출된다.
- 서보 위치는 55도, 110도, 165도이고 이후 0도로 복귀한다.
- 알약 채우기는 웹 버튼을 눌러 55→110→165→0도 순서로 진행한다.
- Teachable Machine 기본 클래스는 1=무드등 켜기, 2=끄기, 3=긴급상황이다.
- 모델 URL은 대시보드의 톱니바퀴 > Teachable Machine 모델 URL에 입력한다.
- 긴급상황은 빨간 LED와 사이렌이 작동하며 팝업의 "확인했습니다"를 눌러야 종료된다.
- WS2812B 색상과 밝기는 대시보드에서 조절하며, DHT 센서는 사용하지 않는다.
- 피에조 부저가 없어도 나머지 기능은 시험할 수 있고 나중에 GPIO 23에 연결할 수 있다.
- OLED는 GPIO 21(SDA), GPIO 22(SCL), SG90은 GPIO 13, IR OUT은 GPIO 27,
  WS2812B DIN은 GPIO 18이다. 모든 전원 GND는 공통이어야 한다.

[권한과 안전]
- 시스템, BLE, 서보, LED, 긴급 경보, 설정, 모델 URL을 직접 변경했다고 말하지 않는다.
- 사용법과 문제 해결은 설명만 한다.
- 유일하게 제안 가능한 변경은 "이미 복용했지만 기록만 누락된 과거/오늘 복약"의
  수동 기록이다. 이때도 actionType=record_manual_dose로 확인 카드를 제안할 뿐,
  기록이 완료됐다고 말하지 않는다.
- 미래 날짜의 복약 완료, 복용하지 않은 약, 불확실한 날짜/시간대는 기록 제안하지 않는다.
- 날짜나 아침/점심/저녁이 불명확하면 먼저 질문하고 actionType=none으로 둔다.
- 사용자의 최근 문맥으로 날짜와 시간대가 명확할 때만 기록 제안을 만든다.
- 약의 복용 여부, 용량 변경, 중복 복용 등 의료 판단은 하지 말고 의료진/약사에게
  확인하도록 안내한다. 긴급한 건강 문제는 즉시 지역 응급 서비스에 연락하도록 안내한다.
- 현재 상태와 최근 기록은 사용자 메시지 끝의 JSON 문맥을 참고하되, 없는 사실은 추측하지 않는다.

[출력]
- reply는 한국어 일반 문장으로 작성한다.
- actionType이 none이면 mealSlot, date, confirmationText는 모두 빈 문자열이다.
- actionType이 record_manual_dose이면 mealSlot은 morning/lunch/evening 중 하나,
  date는 YYYY-MM-DD, confirmationText는 사용자가 확인할 짧은 한국어 문구다.
`.trim();

const outputSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    reply: { type: "string" },
    actionType: {
      type: "string",
      enum: ["none", "record_manual_dose"],
    },
    mealSlot: {
      type: "string",
      enum: ["", "morning", "lunch", "evening"],
    },
    date: { type: "string" },
    confirmationText: { type: "string" },
  },
  required: [
    "reply",
    "actionType",
    "mealSlot",
    "date",
    "confirmationText",
  ],
} as const;

function json(data: unknown, status = 200) {
  return Response.json(data, { status, headers: corsHeaders });
}

function extractOutputText(data: OpenAIResponse) {
  for (const item of data.output ?? []) {
    if (item.type !== "message") continue;
    for (const content of item.content ?? []) {
      if (content.type === "output_text" && content.text) return content.text;
    }
  }
  return "";
}

function isDateKey(value: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00+09:00`);
  return !Number.isNaN(parsed.getTime());
}

function sanitizeAnswer(answer: ModelAnswer, localDate: string): ModelAnswer {
  const safeReply = answer.reply.slice(0, 1200);
  if (
    answer.actionType !== "record_manual_dose" ||
    !mealSlots.includes(answer.mealSlot as MealSlot) ||
    !isDateKey(answer.date) ||
    !isDateKey(localDate) ||
    answer.date > localDate
  ) {
    return {
      reply: safeReply,
      actionType: "none",
      mealSlot: "",
      date: "",
      confirmationText: "",
    };
  }
  return {
    reply: safeReply,
    actionType: "record_manual_dose",
    mealSlot: answer.mealSlot,
    date: answer.date,
    confirmationText: answer.confirmationText.slice(0, 120),
  };
}

export function OPTIONS() {
  return new Response(null, { status: 204, headers: corsHeaders });
}

export async function POST(request: Request) {
  const runtimeEnv = process.env;
  const requestKey = request.headers.get("x-openai-key")?.trim();
  const apiKey = requestKey || runtimeEnv.OPENAI_API_KEY;
  if (!apiKey) {
    return json(
      {
        error:
          "AI 서버에 OPENAI_API_KEY가 설정되지 않았습니다. 서버 환경변수를 확인해 주세요.",
      },
      503,
    );
  }

  try {
    const body = (await request.json()) as AssistantPayload;
    const message = body.message?.trim() ?? "";
    const localDate = body.localDate?.trim() ?? "";
    if (!message || message.length > 1200) {
      return json({ error: "질문은 1~1200자로 입력해 주세요." }, 400);
    }

    const history = (body.history ?? [])
      .filter(
        (item): item is Required<ChatMessage> =>
          (item.role === "user" || item.role === "assistant") &&
          typeof item.content === "string" &&
          Boolean(item.content.trim()),
      )
      .slice(-10)
      .map((item) => ({
        role: item.role,
        content: item.content.slice(0, 1200),
      }));

    const context = {
      localDate,
      appState: body.context ?? {},
      userQuestion: message,
    };
    const response = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: runtimeEnv.OPENAI_MODEL || "gpt-5.6",
        store: false,
        reasoning: { effort: "low" },
        instructions: SYSTEM_INSTRUCTIONS,
        input: [
          ...history,
          {
            role: "user",
            content: `다음 문맥을 참고해 답하세요.\n${JSON.stringify(context)}`,
          },
        ],
        text: {
          format: {
            type: "json_schema",
            name: "pillume_assistant_response",
            strict: true,
            schema: outputSchema,
          },
        },
        max_output_tokens: 700,
      }),
    });

    const data = (await response.json()) as OpenAIResponse;
    if (!response.ok) {
      return json(
        {
          error:
            data.error?.message ||
            "OpenAI 응답을 받지 못했습니다. 잠시 후 다시 시도해 주세요.",
        },
        response.status >= 400 && response.status < 500 ? 502 : response.status,
      );
    }

    const outputText = extractOutputText(data);
    if (!outputText) {
      return json({ error: "AI 응답이 비어 있습니다." }, 502);
    }
    const answer = sanitizeAnswer(
      JSON.parse(outputText) as ModelAnswer,
      localDate,
    );
    return json(answer);
  } catch (error) {
    return json(
      {
        error:
          error instanceof SyntaxError
            ? "AI 응답 형식을 처리하지 못했습니다."
            : "AI 챗봇 연결 중 오류가 발생했습니다.",
      },
      500,
    );
  }
}
