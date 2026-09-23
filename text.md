# Preamble

**TLDR** : *Benchmark scores of "small" open weights models are as good as last year's SOTA paid models. When local inference is needed (data privacy for instance) or preferred (cost), it's totally valid to do agentic coding at scale with the latest ones, such as Qwen 3.8 27B or Qwen3.8-Flash-Next. I do so since a few month, and never looked back. I did this study to make sure my guts feeling was aligned with hard data, and measure the real impact of quantization in multiturn agentic dev scenarios.*

## Disclaimer

This is just my (a random guy) own data and observations based on my own tests with limited time and resources. It may contains errors and mistakes, but also provide some interesting facts and insights...

The scores are from a subset of a public benchmark [sweVerified](https://www.swebench.com/verified.html) covering the **first 100 tasks of the django set**. (Processing all 500 tasks for each model would be too long on my hardware...) This is a benchmark of **agentic AI dev** tasks. A code repo is provided alongside a task and the agent is autonomous until achieved. The agent in question is the lightweight [mini-swe-agent](https://github.com/swe-agent/mini-swe-agent)

If you want to dig even deeper in each of the benchmark traces and see more details, you can do so : [tool calling fine detail analysis](./benchmark-detail.html)

The main goal here is to **compare different local models** and the **impact of different configuration of the same model.** (quantization, inference engine, hardware, finetunes, etc...)

The second goal is to provide some pointers to compare locally run open weights models to paid subscriptions SOTA models.

## A lesson learned: always pin your evaluation workflow.

I was not aware of this fact when starting this project, but by default, running the evaluation workflow from the benchmark will not always 100% sure give the same results. Some improvements and other fixes are still being pushed into the repo, and depending when you build/run the evaluation, the score can change... And since my first tests started a few month back, I did encounter this issue without knowing it, for a while. I learned it the hard way. 

Since the first publication of these numbers, all 78 runs have been re-evaluated under a frozen setup — same evaluation script, same container image and dependency versions, replayed over the saved patch of every task. The score shown everywhere on this page is now that re-verified count: 38 of the 78 runs changed verdict, 9 of them by 5 points or more.

## Some technical information:

Hardware available is (for a total of 192GB VRAM) :

- a single **RTX 6000 Pro Blackwell WS 96 GB VRAM** (limited to 450W)
- two **RTX 4090D** (limited to 300W each) **moded to 48GB**

Models tested with **SGLANG** or **vLLM** run on either the single RTX 6000 or both RTX 4090D.

Bigger local Models are tested with llama.cpp with all three GPUs. llama.cpp is necessary to use the 3 heterogeneous GPUs **and** be able to load the more aggressive quantization.

Some paid API models have been tested through OpenRouter API, for reference.

Most of the bench runs have been set to 5 parallel tasks, except for llama.cpp which is not optimized for concurrency and was limited to 1 request at a time.

When available, **Multi Token Prediction** was enabled. Suggested params from the model creators were applied. Thinking mode enabled for all.

Provider's sampling parameter values have been applied for each model (temp, top_k, etc...)

## Limitations

/!\ Warning about **benchmaxxing**. This reference benchmark is public, so models may oversample this data during their training. A good score on the benchmark is not necessarily an absolute guarantee of good "quality" in real life tasks...

Since I only use a subset of the benchmark, we cannot directly compare with the published scores [on the official site](https://benchlm.ai/benchmarks/sweVerified), but it gives a general idea.

- For reference, one of the latest paid models, **Claude Fable 5 scores 95%**. And the (comparable in size) two year older **Claude 3.5 Sonnet scores 49%**
- Both **Claude Sonnet 4.5 and Qwen 3.6 27B scores 77.2%**. Meaning that **a small local open weight model scores the same as a SOTA paid model from the year before.** which is already impressive.

Python and django tasks only: scores cannot be extrapolated to other languages or domains use cases...

The token generation speed is not relevant here, because it's derived from the benchmark total execution duration divided by the output token number. This duration contains all kinds of overheads related to the benchmark and the agentic harness. But the methodology is consistent between all runs, so we can compare the values between each others.

# Analysis

## Hall of fame

### update Sept 23rd 2026 — complete re-evaluation on a pinned environment

Every run was graded again with a frozen evaluation setup (see the disclaimer above). 

- **Best score overall** : (97) Qwen3.8-Flash-Next AWQ-W4A16 + PLE INT4 (**xhigh**) on vLLM, single RTX 6000
- **Best score local** : (97) same run
- **Best score single GPU** : (97) same run
- **Best score via llama.cpp (3 heterogeneous GPUs)** : (92) Deepseek v4 flash 0731 (Q2_K_XL)
- **Best score paid API** : (77) Deepseek v4 pro, then (76) GLM 5.2
- **Fewer number of request** : (2134) Qwen3.8-Flash-Next AWQ-W4A16 + PLE INT4 (medium) on vLLM (score 89)
- **Most efficient both local and api** (lower request count per point scored) (24) : the same run above
- **Fastest completion** (max concurrency 5) : (43min) Qwen3.8-Flash-Next AWQ-W4A16 (medium) on vLLM (score 86), just ahead of Qwen3.8-27B NVFP4 medium on SGLANG (score 76)
- **Fewest tokens generated** : Hy3 (API) 0.61M
- **Most tokens generated** : Qwen3.5-35B-A3B **Ornith-1.5** 4.0M (also the best score of the 35B-A3B family: 80)

The entries below are kept exactly as they were written on their date, for transparency. Their scores come from the old unpinned evaluation pass and are **superseded** by the numbers above and by the tables.

### update Sept 4th 2026

Support for **Qwen3.8-Flash-Next** for different hardware and engines is still moving. I just tested another configuration, this time for vLLM and... WOW! While it's slower than the previous SGLANG patch I used, it's way better !

- **Best score overall** : (98) Qwen3.8-Flash-Next AWQ-W4A16 + PLE INT4 (medium) on vLLM
- **Best score local** : (98) Qwen3.8-Flash-Next AWQ-W4A16 + PLE INT4 (medium) on vLLM
- **Best score single GPU** : (98) Qwen3.8-Flash-Next AWQ-W4A16 + PLE INT4 (medium) on vLLM
- **Fewer number of request** : (2134) Qwen3.8-Flash-Next AWQ-W4A16 + PLE INT4 (medium) on vLLM
- **Most efficient both local and api** (lower request count per point scored) (22) : Qwen3.8-Flash-Next AWQ-W4A16 + PLE INT4 (medium) on vLLM

### update August 28th 2026

**Qwen3.8-Flash-Next** has just been released, as a technological preview of the new Qwen architecture. And... it's very good ! AND fast ! AND efficient (in medium reasoning) !

- **Most efficient both local and api** (lower request count per point scored) (29) : Qwen3.8-Flash-Next NVFP4 + PLE FP8 (medium) on SGLANG

It's very close second in overall max score (91 compared to 92) and not far for fastest completion (1h03 compared to 45-ish min)

### update August 17th 2026

**Qwen 3.8 27B** has been released a few days ago... It's a nice upgrade! It's now the most efficient local model (only in medium reasoning effort)

- **Most efficient local** (lower request count per point scored) (33) : Qwen3.8-27B medium BF16 BF16 (other quants of the same model very close)
- **Fastest completion** (max concurrency 5) : (43min)  Qwen3.8-27B medium NVFP4 FP8 

### update August 7th 2026

I tested other quants of DSV4F, and got even higher scores (90+). The even more interesting part is that the lower quant of them all got the higher score! But trails behind at efficiency (nb request per point)

- **Best score overall** : (92) Deepseek v4 flash 0731 (Q2_K_XL) 
- **Best score local** : (92) Deepseek v4 flash 0731 (Q2_K_XL) 

### update August 3rd 2026

**DeepSeek V4 Flash 0731** update came out...

- **Best score overall** : (81) Deepseek v4 flash 0731 (MXPF4)
- **Best score local** : (81) Deepseek v4 flash 0731 (MXPF4)
- **Most efficient local** (lower request count per point scored) : Deepseek v4 flash 0731 (MXFP4)

### at July 20 2026

- **Best score overall** : (80) tie Deepseek v4 pro (API) & GLM 5.2 (API) 
- **Best score local** : (79) tie MiniMax-M2.7 Q4_K_M & DeepSeek v4 Flash Q3_K_XL
- **Best score single GPU** : (76) Qwen3.6 27B BF16 FP8
- **Worst score** : (56) Gemma-4-26B-A4B-it BF16 FP8
- **Most efficient local** (lower request count per points scored) : Gemma-4-31B-it 
- **Less tokens generated** : Hy3 : 0.62M
- **Most tokens generated** : tie Ornith-1.0-35B & Gemma-4-26B-A4B-it with 2.2M (almost 4x more)

## About Score and Efficiency

| Model quant   | Score | Efficiency (Req/pt) |
|---------------|-------|---------------------|
| DSV4F Q2_K_XL | 88-92 | 51 avg              |
| DSV4F Q3_K_XL | 90    | 42                  |
| DSV4F Q8_K_XL | 90    | 42                  |
| DSV4F MXFP4   | 79-85 | 33 avg             |

The score value doesn't say the whole story. Yes it solved more tasks, upto 7 points difference is significant.

But, checking the Efficiency (Avg number of requests needed to solve one task) it's the other way around : Q2 needed more than half again more requests than MXFP4 to score 1 point, in average! Why ?

Why ? it's still unclear... It's not user error, since I used the exact same setup for the all of them. Exact same llama.cpp command line.

Some Papers say than the tiny errors added by the quantization can, sometimes, be beneficial for certain tasks... 

It seems that the MXFP4 produces valid submit commands earlier — it reads the repo, writes a patch, and decides "done" sooner. That's why it has 13 trajectories at ≤10 requests (the k-quants have 2–6). The k-quants' extra requests are spent iterating — more read/edit/test cycles before submitting. Maybe making some mistakes trigger the model explore more.

## About cost...

The cost of API LLMs are the cost directly billed by the OpenRouter provider.

The cost of locally run LLMs have been estimated base on the average power draw of the rig (about 700W), the duration of the test, and a cost of 0.2$ per KWh (which is relevant for France, but maybe not for other part of the world...)

However... The initial cost of the rig itself, while very significant, is not part of this discussion... You obviously need to account for it in order to estimate any long term rentability.

- Gemma 4 dense local, being less chatty, is even twice cheaper than Qwen 3.6 dense local models.
- Minimax 2.7 Q4 local or Deepseek v4 flash Q3 local cost about 1 dollar for the full run and, once re-verified, match or beat the recent GLM 5.2 (76) : 77 and 90. N.B. the cost for bigger models run with llama.cpp are impacted by the concurrency limitation. We could expect it to be 5 times cheaper if run with SGLANG or vLLM with the adequate hardware. (2x RTX Pro 6000 BW for instance)
- An expensive GPU price can be hard to justify as a single dev, but for a small team of 5 or 10, one (or more) 15k$ GPU can be quickly paid off...

## Generalities

- Keep in mind that the benchmark contains 100 complex tasks, each resolved in multi turns (around 50 in average), tool use etc... Having 70 of them being successfully resolved in a few hours by a locally run open weights model is already impressive.
- "Larger" models, even quantized, are often qualitatively better than smaller non-quantized models. But (depending on the hardware) significantly slower, which can hinder one's (or a team's) productivity...
- In general, for similar sizes, dense models score better than their MoE counterparts (but are slower, of course).
- **Quantization variants of dense models** (FP8, weights and/or cache) have similar scores. (Gemma4 31B / Qwen3.6 27B).
- It is **the opposite for MoE models** (Gemma4 26B-A4B / Qwen3.6 35B-A3B) which seem to degrade significantly.

## Model-Specific observations

### Qwen 3.X 35B-A3B MoE family

#### original 3.5 35B-A3B *score=68* 

This MoE model is fast, but was not so good with tools, but a recent promising finetune has been released :

#### Ornith-1.0-35B *score=74*

is a finetune of the older Qwen3.5-35B-A3B, and has a very good score for its category. We see that it generates many more requests and tokens to achieve this in twice as much time as Qwen3.6-35B-A3B. This could have one or more explanations:

- The model was trained to lengthen its "chain-of-thought" during "thinking"
- The model makes more mistakes, incorrect tool calls, and generating code bugs that it must later fix
- while still being a little better than the original model, since it scored higher (+6).

Trying to understand, let's see the details in [tool calling fine detail analysis](./benchmark-detail.html) 

- the model generated a lot more of tool calls (8327 vs 7546)
- but generated less tool call errors (Non-zero return codes) in total (489 vs 739)
- being at the end twice as "precise" (5.87% errors vs 9.79%)
- looking at the error details, there is no significant change in the distribution.

The models tries harder, generate less tool call errors and scores higher, which seems a good finetune result.

#### Ornith-1.5-35B *score=80*

The new version of the same finetune is now the best of the whole 35B-A3B family (+12 over the original Qwen3.5-35B-A3B).

#### GRM-3.2-Sky *score=71*

Another finetune of the same base, in between (+3), at the same cost as Ornith-1.0.

#### Qwen 3.6 35B-A3B *score=60*

TBD

### Gemma-4 26B-A4B MoE *score=54* 

Fast but Quite poor.

### Gemma-4 31B *score=67-73*

Nice score, and one of the most efficient for the requests / score ratio. It's actually the most efficient of the local models (45 req/pt), if we exclude the Qwen3.8-Flash-Next family. Some people say it is "lazy", meaning it's not trying has hard as it could. Maybe a 4.1 version trained to try harder could be very good!

This model is praised for its writing ability, so I keep using it for others tasks than coding.

### Qwen3.6 27B family *score=69-76*

Probably the best coding LLM for its size when it was released. Only to be replaced by the 3.8 version a few month later.

#### Qwen3.6 27B heretic-v2 *score=70-73*

An uncensored version, which managed to preserve most of it's intelligence. Useful if you still need to know what really happened in Tienanmen, or just not a fan of the guardrails baked into the models.

#### ThinkingCap Qwen3.6 27B *score=69*

A finetune version trained to be more efficient and generate less tokens (and less requests), which is achieved, but at the cost of a few score points. Very good finetune nonetheless.

### Qwen3.5 122B-A10B *score=70*

This one was my previous favorite. Its size 122B pack a bunch of knowledge and with only 10B active parameters it was fast. (The upgraded 3.8 flash next version with an added ngram table is kicking ass!)

### Qwen3.8 27B family *score=74-83*

The best local model for the size. Also robust to quantization (being a dense model).

#### medium reasoning *score=74-81*

In **medium** reasoning mode, it both scores higher than the 3.6 version, AND is very efficient (about 55% of the requests of the xhigh runs, and less than a third of the tokens generated). The heretic-ara (INT8) and Huihui-abliterated (FP8) finetunes reach 80, so uncensoring costs nothing here.

#### xhigh reasoning *score=82-83*

The **xhigh** mode is advertised to be the best one for hard tasks, and after the re-evaluation the gain is finally visible : +4 pts over medium, consistently across quants and engines. The price is ~70% more requests and more than 3 times the tokens. For a daily coding agent I'd still stay on medium, for the last few percent of hard tasks use xhigh.

### Qwen3.8-Flash-Next *score=75-97*

Incredibly good (yet still undertrained) model with a new architecture that will probably become outstanding once fully trained. Qwen4 soon !

#### medium reasoning *score=84-90*

In **medium** reasoning mode it holds the best efficiency of all models tested : 89 at 24 req/pt (vLLM, AWQ-W4A16) and 90 at 29 req/pt (SGLANG, NVFP4), both in about an hour. 

#### xhigh reasoning *score=93-97*

This is where xhigh pays for real : 97, the best score of the study, for ~60% more requests and twice the tokens than medium. Still the chattiest of the family, but the gain is now measurable.

### Muse-Glimmer-30B *score=73-76*

Dense 30B on the single RTX 6000. Score in the Qwen3.6-27B range, but extremely chatty : 8.5k to 9.5k requests for those points (115-127 req/pt, twice a Qwen3.6-27B). The heretic finetune is indistinguishable from the base model (73-75 vs 74-76).

### Bigger models via llama.cpp

#### MiniMax-M2.7 Q4_K_M *score=77*

Very good model, even highly quantized. It now matches the best API model I tested (Deepseek v4 pro, 77) and beats GLM 5.2. And very efficient too, with just 1.1M token generated.

#### Deepseek v4 flash 0731 Q2_K_XL / Q3_K_XL / Q8_K_XL *score 90-92*

Both highly quantized k-quants of the release score 90+. 

#### Deepseek v4 flash 0731 MXFP4 *score 79-85*

When it came out it was very good. One of the most efficient too, 7 points behind the Q2_K_XL run that costs 50 req/pt.

Very strong model! Too bad it was lacking vision support...

Running at 50 tokens/s without speculative decoding via DSpark.

With Dspark enabled for 3 predicted tokens, I reached 95 tokens/s average for the whole benchmark run (looking at the actual inference logs). Dspark degrades the prefill speed, but the boost in generation is totaly worth it. The run with dspark took 4 to 5 hours instead of 6 to 7 hours.

#### DeepSeek-V4-Flash-Vision-Exp (Q3_K_XL) *score 81*

Now with vision! Same base model and quantization as the Q3_K_XL above, but 6 points lower and paid for with 4219 requests and 11h25 of wall time (the slowest run of the study).

### Bigger models yet to be tested locally (maybe someday...)

#### Tencent Hy3 *score=70*

Tested on the cloud has proved to get a decent score while being the most efficient of all the API models (38 req/pt, 0.61M tokens generated). I shall test it soon locally.

#### Xiaomi Mimo 2.5 *score=70*

Has the same score, but is way less efficient (61 req/pt, 1.82M tokens).

## Impact of Model Weights Quantization

On consumer GPUs limited in VRAM, it is often mandatory to quantize (compress) the model weights to be able to load it on the GPU.

Roughly, switching from BF16 to FP8 will halve the size of the model weights. BF16 to AWQ 4bit or NVFP4 will divide it by 4.

It is estimated that the precision loss of FP8 is negligible. It depends...

### Gemma4 31B

The re-verified runs span 67 to 73 depending on weights quantization, KV cache quantization and chat template. The BF16 weights runs are 72-73, the FP8-dynamic ones 67-71, but they don't order consistently (FP8 weights with FP8 cache scored 71 against 67 for BF16 cache). 

### Qwen3.6 27B

Some small impact on the score : the FP8 weights run scored 72 against 75 for the same configuration in BF16. **When possible**, it is better to avoid it...

## Impact of KV cache Quantization

To increase the context size available it is also useful to quantize the KV cache (size of 150kt is my sweet spot).

Even if the score is not negatively impacted by KV Cache quantization, it generates more requests and more tokens, an indication of more errors generated. **If possible**, it's better to avoid it.

### Gemma4 31B BF16 && Gemma4 31B FP8 (vLLM)

FP8 KV cache costs 1 point on the BF16 weights pair (73 -> 72) and gains 4 on the FP8 weights pair (67 -> 71). Both effects are inside the noise band measured in the disclaimer, and the requests/token counts don't move in a consistent direction. The initial observation that it generated more requests, but fixed its own errors, is not reproduced on all pairs.

### Qwen3.6 27B BF16 (SGLANG)

Quantizing the KV cache to FP8 has no negative impact on the score (72 vs 75 on the 2 GPU pair) and very little on the other metrics.

### Qwen3.6 27B FP8 (SGLANG)

The FP8 quantized weights with FP8 cache scored 72 with 5285 requests, against 75 with BF16 weights and the same cache. The score difference is the quantization of the weights, not of the cache.

## Context sizes

Max context size available for 96GB VRAM, as logged by the engines, with GPU utilization between 0.9 and 0.95 (some tweaking on VRAM usage might allow to get a little more)

On some VRAM limited setup, many other tweaks can help (dropping the vision capability, removing MTP, etc...)

The benchmark was run with a target of 150kt and 5x concurrency. So, if all 5 use the max size configured, we need 750kt total, but in practice, we never got there. But it did sometimes reach maximum capacity. Before this limit was reached, no impact was seen. After, some speed loss was seen (to swap context between each concurrent requests...) until a task is finished and released all its allocated token capacity.

Qwen and Gemma models have different architectures and attention mechanisms, so each token in cache uses a different amount of bytes in VRAM.

#### Qwen3.6 27B

| Engine | Weights | Cache | total max tokens | Notes |
|--------|---------|-------|------------------|-------|
| SGLANG |    BF16 |  BF16 |             287k | ❌ no enough: speed drop around task 60 for 15 min. |
|   vLLM |    BF16 |  BF16 |             404k | ✅ for this bench, but limit to x3 concurrency worst case |
| SGLANG |    BF16 |   FP8 |             574k | ✅ for this bench, but limit to x4 concurrency worst case  |
|   vLLM |    BF16 |   FP8 |             752k | ✅✅ for x5 concurrency worst case |
| SGLANG |     FP8 |  BF16 |             564k | ✅ for this bench, but limit to x4 concurrency worst case |
|   vLLM |     FP8 |  BF16 |             730k | ✅✅ for this bench, almost enough for x5 worst case |
| SGLANG |     FP8 |   FP8 |            1128k | ✅✅ even for x7 concurrency worst case |
|   vLLM |     FP8 |   FP8 |            1359k | ✅✅ even for x9 concurrency worst case |

vLLM is more efficient in handling KV cache in VRAM.

#### Gemma4 31B

| Engine | Weights | Cache | total max tokens | Notes |
|--------|---------|-------|------------------|-------|
| SGLANG |     FP8 |   FP8 |             114k | ❌ no enough |
|   vLLM |     FP8 |   FP8 |             757k | ✅✅ for x5 concurrency worst case |

vLLM efficiency for KV cache is even more visible with Gemma4.


## Personal notes and things to investigate

- Test bigger models with llama.cpp on all 3 GPUs
- Test GGUFs in vLLM/SGLANG
- 