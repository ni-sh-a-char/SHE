from she import run, Number

while True:
    text = input('SHE > ')
    if text.strip() == "":
        continue

    result, error = run('<stdin>', text)

    if error:
        print(error.as_string())
    # Completely suppress printing the return value of run function
    # since PRINT already outputs to console
    else:
        stripped_text = text.strip()
        if stripped_text.startswith("RUN(") or stripped_text.startswith("PRINT"):
            continue
        if result is None or result == Number.null:
            continue
        else:
            print_result = True
            if result == Number.null:
                print_result = False
            elif hasattr(result, 'elements') and len(result.elements) == 1:
                print(repr(result.elements[0]))
                print_result = False
            if print_result:
                print(repr(result))
