# 🛡️ SUB_Tracker Mobile: Rules of Engagement

As defined by the Lead Mobile Architect, all development in `sub_tracker_app` must strictly adhere to these 5 laws. Violation of these rules triggers a critical system error.

### 1. Zero-UI-Breaking Rule
- Logic changes (Riverpod/State) must **never** break layout.
- UI components in the `presentation` layer must remain **dumb**—they only consume state and trigger events.

### 2. Strict Layering (Clean Architecture)
- **Forbidden**: Importing files from `data/` directly into `presentation/`.
- Interaction must go strictly through `domain/` (Interfaces/UseCases) or abstract Riverpod providers.

### 3. Data Immutability
- All models (`entities`, `DTOs`) and state classes **must** use `freezed`.
- No mutable variables (no `var`, no `late` without initialization) in state classes.

### 4. Robust Error Handling
- All API/Dio errors must be caught in the **Repository** layer.
- Errors must be converted into a `Failure` object (or `Either<Failure, T>`) using `fpdart`.
- The UI must handle `failure` states gracefully without crashing.

### 5. Widget Modularity
- Any widget exceeding **50 lines** must be extracted into a separate file within `presentation/widgets/`.
- Keep build methods clean and readable.

---
*Signed, Lead Mobile Architect & Senior Flutter Developer*
