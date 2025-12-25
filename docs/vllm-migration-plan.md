# vLLM 전환 계획서

> 작성일: 2025-12-25
> 버전: 1.0
> 상태: 계획 단계

---

## 1. 개요

### 1.1 목적
현재 Ollama 기반 LLM 서빙을 vLLM으로 전환하여 동시 사용자 처리 용량을 대폭 향상시킨다.

### 1.2 배경
- 현재 시스템: Ollama + Qwen3 32B
- 동시 처리 한계: 1-2명 (실시간 응답 기준)
- 주요 병목: LLM 추론 속도 및 동시 요청 처리

---

## 2. 현재 시스템 분석

### 2.1 하드웨어 사양

| 구성 요소 | 사양 |
|-----------|------|
| CPU | 20 코어 |
| 메모리 | 119GB (67GB 가용) |
| GPU | NVIDIA GB10 |
| VRAM | ~26GB 사용 가능 |

### 2.2 현재 성능 (Ollama)

| 모델 | 토큰/초 | 100토큰 생성 시간 |
|------|---------|-------------------|
| qwen3:32b | 9.9 | 10.3초 |
| phi4-mini | 79.7 | 1.5초 |

### 2.3 현재 동시 사용자 수

| 시나리오 | qwen3:32b | phi4-mini |
|----------|-----------|-----------|
| 실시간 응답 | 1-2명 | 8-10명 |
| 대기 허용 (30초) | 3-5명 | 15-20명 |

---

## 3. vLLM 전환 기대 효과

### 3.1 성능 향상 예측

#### 벤치마크 기반 예측 (업계 데이터)

| 지표 | Ollama | vLLM | 개선율 |
|------|--------|------|--------|
| 최대 처리량 (TPS) | 41 | 793 | **19배** |
| P99 지연시간 | 673ms | 80ms | **8배 개선** |
| 동시 128명 처리 | 기준 | 3.2배 | **3.2배** |

#### 예상 토큰 생성 속도

| 모델 | Ollama (현재) | vLLM (예상) | 개선율 |
|------|---------------|-------------|--------|
| Qwen2.5-32B | 10 토큰/초 | 30-50 토큰/초 | **3-5배** |
| Phi-4 (3.8B) | 80 토큰/초 | 150-200 토큰/초 | **2-2.5배** |

### 3.2 동시 사용자 수 예측

#### Qwen2.5-32B 모델 기준

| 시나리오 | Ollama (현재) | vLLM (예상) | 개선율 |
|----------|---------------|-------------|--------|
| 실시간 응답 | 1-2명 | 5-10명 | **5배** |
| 대기 허용 (30초) | 3-5명 | 15-25명 | **5배** |
| 최대 동시 처리 | 5-8명 | 30-50명 | **6배** |

#### Phi-4 모델 기준 (vLLM)

| 시나리오 | 예상 동시 사용자 |
|----------|------------------|
| 실시간 응답 | 30-50명 |
| 대기 허용 (30초) | 80-100명 |
| 최대 동시 처리 | 150-200명 |

### 3.3 핵심 기술 이점

| 기술 | 설명 | 효과 |
|------|------|------|
| **PagedAttention** | 비연속 KV 캐시 메모리 관리 | 메모리 효율 최대 24배 향상 |
| **Continuous Batching** | 동적 요청 배칭 | 처리량 대폭 증가 |
| **Optimized CUDA Kernels** | GPU 최적화 커널 | 추론 속도 향상 |
| **Tensor Parallelism** | 다중 GPU 분산 | 확장성 확보 |

---

## 4. 전환 계획

### 4.1 아키텍처 변경

```
[현재]
┌─────────────────────────────────────────────────────────┐
│  Backend (FastAPI)                                      │
│  └── LangChain ChatOllama ──→ Ollama Server ──→ LLM    │
│  └── LangChain OllamaEmbeddings ──→ Ollama ──→ BGE-M3  │
└─────────────────────────────────────────────────────────┘

[전환 후]
┌─────────────────────────────────────────────────────────┐
│  Backend (FastAPI)                                      │
│  └── LangChain ChatOpenAI ──→ vLLM Server ──→ LLM      │
│  └── LangChain OllamaEmbeddings ──→ Ollama ──→ BGE-M3  │
└─────────────────────────────────────────────────────────┘
```

### 4.2 변경 대상 파일

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `backend/src/core/config.py` | 수정 | vLLM 설정 추가 |
| `backend/src/core/llm.py` | 수정 | vLLM 래퍼 클래스 추가 |
| `docker/docker-compose.yml` | 수정 | vLLM 서비스 추가 |
| `docker/.env` | 수정 | vLLM 환경변수 추가 |
| `backend/requirements.txt` | 수정 | langchain-openai 추가 |

### 4.3 단계별 전환 계획

#### Phase 1: 준비 (1단계)
- [ ] vLLM 로컬 테스트 환경 구축
- [ ] HuggingFace 모델 다운로드 (Qwen2.5-32B-Instruct)
- [ ] vLLM 서버 단독 실행 테스트
- [ ] 성능 벤치마크 측정

#### Phase 2: 코드 수정 (2단계)
- [ ] `config.py`에 vLLM 설정 추가
- [ ] `llm.py`에 VLLMChat 클래스 구현
- [ ] 백엔드 선택 로직 구현 (ollama/vllm 스위칭)
- [ ] 단위 테스트 작성

#### Phase 3: 통합 (3단계)
- [ ] Docker Compose에 vLLM 서비스 추가
- [ ] 환경변수 설정
- [ ] 통합 테스트 실행
- [ ] 스트리밍 응답 검증

#### Phase 4: 배포 (4단계)
- [ ] 스테이징 환경 배포
- [ ] 부하 테스트 실행
- [ ] 모니터링 설정
- [ ] 프로덕션 배포

---

## 5. 상세 구현 가이드

### 5.1 vLLM 서버 실행

```bash
# vLLM 설치
pip install vllm

# 서버 실행
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-32B-Instruct \
    --host 0.0.0.0 \
    --port 8001 \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.9 \
    --max-model-len 8192 \
    --enable-chunked-prefill
```

### 5.2 Docker Compose 설정

```yaml
vllm:
  image: vllm/vllm-openai:latest
  container_name: graphrag-vllm
  ports:
    - "18001:8000"
  volumes:
    - vllm_cache:/root/.cache/huggingface
  environment:
    - HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}
  command: >
    --model Qwen/Qwen2.5-32B-Instruct
    --gpu-memory-utilization 0.9
    --max-model-len 8192
    --enable-chunked-prefill
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
  networks:
    - graphrag-network
  restart: unless-stopped
```

### 5.3 환경변수 설정

```bash
# docker/.env 추가
LLM_BACKEND=vllm                              # ollama 또는 vllm
VLLM_BASE_URL=http://vllm:8000/v1            # vLLM 서버 URL
VLLM_MODEL=Qwen/Qwen2.5-32B-Instruct         # HuggingFace 모델명
HF_TOKEN=your_huggingface_token              # HuggingFace 토큰
```

### 5.4 config.py 수정

```python
# vLLM Settings
vllm_base_url: str = Field(default="http://localhost:8001/v1")
vllm_model: str = Field(default="Qwen/Qwen2.5-32B-Instruct")
llm_backend: str = Field(default="ollama")  # "ollama" or "vllm"
```

### 5.5 llm.py 수정 (VLLMChat 클래스)

```python
from langchain_openai import ChatOpenAI

class VLLMChat:
    def __init__(self, model: str = None, base_url: str = None, temperature: float = 0.7):
        self.model = model or settings.vllm_model
        self.base_url = base_url or settings.vllm_base_url

        self._llm = ChatOpenAI(
            model=self.model,
            base_url=self.base_url,
            api_key="EMPTY",  # vLLM은 API 키 불필요
            temperature=temperature,
            streaming=True,
        )

    async def generate_stream(self, user_message: str, ...) -> AsyncIterator[str]:
        messages = self._build_messages(user_message, system_prompt, chat_history)
        async for chunk in self._llm.astream(messages):
            if chunk.content:
                yield chunk.content
```

---

## 6. 리스크 및 대응 방안

### 6.1 잠재적 리스크

| 리스크 | 영향도 | 대응 방안 |
|--------|--------|-----------|
| 모델 호환성 | 중 | HuggingFace 포맷 모델 사전 테스트 |
| GPU 메모리 부족 | 고 | 양자화 모델 사용 (AWQ/GPTQ) |
| 콜드 스타트 지연 | 중 | 모델 프리로딩 설정 |
| 서비스 중단 | 고 | 롤백 계획 수립, Ollama 병행 운영 |

### 6.2 롤백 계획

1. 환경변수 `LLM_BACKEND=ollama`로 변경
2. Backend 컨테이너 재시작
3. vLLM 컨테이너 중지

---

## 7. 모니터링 및 검증

### 7.1 성능 지표

| 지표 | 측정 방법 | 목표 |
|------|-----------|------|
| 토큰/초 | vLLM 메트릭스 | >30 (32B 모델) |
| P99 지연시간 | Prometheus | <500ms |
| 동시 처리량 | 부하 테스트 | >10명 (실시간) |
| GPU 사용률 | nvidia-smi | <90% |

### 7.2 검증 체크리스트

- [ ] 스트리밍 응답 정상 동작
- [ ] 한국어 응답 품질 유지
- [ ] 컨텍스트 유지 (대화 히스토리)
- [ ] 에러 처리 정상 동작
- [ ] 동시 10명 이상 처리 확인

---

## 8. 비용 분석

### 8.1 추가 리소스 요구사항

| 항목 | Ollama (현재) | vLLM (예상) |
|------|---------------|-------------|
| GPU 메모리 | ~20GB | ~22GB |
| 시스템 메모리 | ~4GB | ~8GB |
| 디스크 (모델) | 20GB (GGUF) | 60GB (HF) |
| 초기 로딩 시간 | ~30초 | ~60초 |

### 8.2 ROI 분석

| 항목 | 현재 | 전환 후 |
|------|------|---------|
| 동시 사용자 | 2명 | 10명 |
| 사용자당 비용 | 100% | **20%** |
| 확장성 | 제한적 | 우수 |

---

## 9. 타임라인

| 단계 | 작업 | 예상 소요 |
|------|------|-----------|
| Phase 1 | 준비 및 테스트 | 1일 |
| Phase 2 | 코드 수정 | 0.5일 |
| Phase 3 | 통합 테스트 | 0.5일 |
| Phase 4 | 배포 | 0.5일 |
| **총합** | | **2.5일** |

---

## 10. 결론

### 10.1 기대 효과 요약

| 항목 | 현재 | 전환 후 | 개선율 |
|------|------|---------|--------|
| 동시 사용자 (실시간) | 1-2명 | 5-10명 | **5배** |
| 동시 사용자 (대기 허용) | 3-5명 | 15-25명 | **5배** |
| 토큰 생성 속도 | 10/초 | 30-50/초 | **3-5배** |
| P99 지연시간 | 673ms | 80ms | **8배** |

### 10.2 권장 사항

1. **단기**: phi4-mini로 Ollama 유지 (즉시 8배 성능 향상)
2. **중기**: vLLM 전환으로 동시 처리 용량 확대
3. **장기**: 다중 GPU 또는 분산 vLLM 클러스터 구축

---

## 부록

### A. 참고 자료

- [vLLM 공식 문서](https://docs.vllm.ai/)
- [vLLM GitHub](https://github.com/vllm-project/vllm)
- [LangChain OpenAI Integration](https://python.langchain.com/docs/integrations/chat/openai)

### B. 관련 문서

- `docker/docker-compose.yml` - Docker 설정
- `backend/src/core/llm.py` - LLM 래퍼 코드
- `backend/src/core/config.py` - 설정 파일
