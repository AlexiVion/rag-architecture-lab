# ADR-0006 — Reserve Tiny World Models & Physical AI as a future, separate research track

- Date: 2026-11-08
- Status: **Proposed / not implemented / not benchmarked**
- Owner intent: explore physical AI and world models after discussing plant-mediated control, low-neuron biological circuits and minimal intelligence.
- Track: [PHY issue #12](https://github.com/AlexiVion/rag-architecture-lab/issues/12)
- Scientific home: bio-inspired minimal intelligence, model-based reinforcement learning, dynamical systems and physical AI
- Research boundary: a separate, currently unimplemented research topic; not part of the active evidence-grounded QA study

## Thesis

An agent need not generate text or realistic video to have an actionable world model. For a specific embodied task, learn a low-dimensional representation of state and **action-conditioned forward dynamics**, then plan or control behavior in a closed loop.

Scientific question: *What is the smallest measured complete system (perception + state estimation + predictive dynamics + planner/control) that meets a preregistered success/robustness target under partial observability, while generalizing to unseen dynamics?*

Do not mistake a learned light-reactive controller for a world model unless it actually predicts a consequence of candidate actions and those predictions are used or evaluated.

## Research taxonomy

1. Control theory: state estimation, filters, system identification, PID, MPC, robust/adaptive control; extremely strong, inexpensive baselines.
2. Model-free RL: recurrent and feedforward controllers; performance/experience baselines without learned predictive dynamics.
3. Tiny learned world models: linear transitions, RNN/GRU, sparse recurrent networks, small RSSM and ensembles; compare prediction against action-conditioned rollout accuracy.
4. Bio-inspired dynamical controllers: integrate-and-fire, neural circuit policies/LTC, plant-like signal integration and decay, reservoirs; use equivalent sensor/action interface.
5. Embodied systems / morphology: information processing performed by the environment, sensor configuration, passive physics, contact dynamics.
6. Physical foundation-model scaling: V-JEPA, Dreamer, TD-MPC and Cosmos as **literature references**, not assumed computationally available baselines on consumer CPU.
7. Sim-to-real and safety: actuator saturation, sensor noise, delay, collision and energy cost, emergency stop, domain randomization.

## Critical prior work

- [World Models, Ha & Schmidhuber (2018)](https://worldmodels.github.io/): 867-parameter controller was only one module; encoder ~4.35M plus MDN-RNN ~422K.
- [Neural Circuit Policies (Nature Machine Intelligence 2020)](https://www.nature.com/articles/s42256-020-00237-3): 19 neurons in a **task-specific steering subcontroller**, with 32 upstream features; not the whole driving pipeline.
- [DreamerV3 (Nature 2025)](https://www.nature.com/articles/s41586-025-08744-2): imagined trajectory model-based RL.
- [TD-MPC2 (ICLR 2024)](https://proceedings.iclr.cc/paper_files/paper/2024/hash/cf73d57b6dcda32b293df7c2d5341f49-Abstract-Conference.html): latent model predictive control.
- [V-JEPA 2 (Meta 2025)](https://ai.meta.com/research/publications/v-jepa-2-self-supervised-video-models-enable-understanding-prediction-and-planning/): self-supervised video prediction with robotic planning adaptation.
- [NVIDIA Cosmos (2025–26)](https://github.com/NVIDIA/cosmos): world foundation models for Physical AI; requires far greater compute than this initial plan.
- [MuJoCo](https://github.com/google-deepmind/mujoco): mature physics engine.
- [Gymnasium classic control](https://gymnasium.farama.org/v1.2.1/environments/classic_control/): small stable baselines.
- [World model taxonomy and uncertainty (2026)](https://link.springer.com/article/10.1007/s44163-026-02122-1): detailed prior-art classification.

## First benchmark design — a moving light with noisy sensors

A simulated mobile agent has left/right light intensity, distance sensors and bounded motor torque; partially observed dynamics, moving light, obstacle geometry, energy cost and finite observation/action rates. This is a *design hypothesis*, not a completed environment.

### Matched controllers

- A deterministic light-following policy and PID controller (simple baselines).
- Exact known simulator dynamics / MPC planner as an **oracle** diagnostic; clearly labeled as not learned.
- Model-free MLP and tiny recurrent policy.
- Learned low-dimensional linear state-space dynamics + planning.
- Learned small sparse recurrent/GRU or RSSM world model + planning.
- Optional bio-inspired reservoir, LIF, NCP/LTC; compare them only under matched budgets.

### Scientific controls

- The world model must predict `p(s_{t+1}|s_t,a_t)` or equivalent belief-state transitions; compare **multi-step rollout accuracy and downstream action success**, not only one-step MSE.
- Fix observations and actuators, and report any privileged state access as oracle control; do not compare hand-given true coordinates to image-input networks without stratification.
- Measure **entire stack**: model parameter total (trainable and fixed), memory, compiled byte size, state memory, training environment interactions, inference p50/p95 CPU milliseconds, prediction calibration, physical success and worst-case failures. Only report real energy measurements when instrumentation exists.
- Randomize environment geometry, moving light, sensor noise, delays and force constants; freeze train/dev/evaluation seeds. Use at least a small preregistered unseen dynamics suite and multiple training seeds with confidence intervals.
- Mark simulated performance as **simulation only**. Do not claim physical robustness without real hardware tests.
- Evaluate any learned simulator's predictive error alongside control results. Better prediction may not mean better control; negative results must be kept.
- All experiments possible without a real robot, cloud API or GPU as a starting requirement; MuJoCo may follow after lightweight 2D environment proves the protocol.

## Outcome and scoping

Successful *paper-ready* work would be a preregistered, reproducible comparison showing whether the tiny world model beats rule-based, model-free, linear-model and similar-sized recurrent baselines on heldout dynamics in sample-efficiency and control/compute trade-offs. A negative result also counts if faithfully reported.

**Do not redirect near-term development from MICRO evidence-efficient RAG to robotics yet.** Keep related benchmarking infrastructure and shared scientific standards; separate datasets, methods, licenses, hardware validation and release criteria.

See [PHY issue #12](https://github.com/AlexiVion/rag-architecture-lab/issues/12) for the complete backlog.
