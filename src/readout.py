import logging
import math


# logger.debug("STOP TESTING")
# result = convertReadoutToValue(cnnAnalogResults, "Analogue100", True, -1)
# logger.debug(f"Analog readout result: {result}")
# firstDigit = result[0] if result != "" else -1
# result = convertReadoutToValue(
#    cnnDigitalResults, "Digital", False, int(firstDigit)
# )
# logger.debug(f"Digital readout result: {result}")
# logger.debug("STOP TESTING")

INVALID_DIGIT = "N"

ANALOG_ERROR = 3
DIGITAL_UNCERTAINTY = 0.2
DIGITAL_TRANSITION_AREA_PREDECESSOR = 0.7  # 9.3 - 0.7
DIGITAL_BAND = 3

# Pre-run zero crossing only happens from approx. 9.7 onwards
DIGITAL_TRANSITION_AREA_FORWARD = 9.7

logger = logging.getLogger(__name__)


def convertReadoutToValue(
    vals,
    CNNType: str,
    extendedResolution=False,
    prev: int = 0,
    beforeNarrowAnalog=0,
    analogDigitalTransitionStart=0,
) -> str:
    result = ""

    analogValues = []
    for val in vals:
        analogValues.append(val.value)

    if len(analogValues) == 0:
        return result

    logger.debug(
        f"getReadout analogValues={analogValues}, "
        f"extendedResolution={extendedResolution}, "
        f"prev={prev}"
    )

    if CNNType in {"Analogue", "Analogue100"}:
        number = float(analogValues[-1])
        result_after_decimal_point = (int(number * 10) + 10) % 10

        prev = PointerEvalAnalogNew(number, prev)
        result = str(prev)

        if extendedResolution:
            result += str(result_after_decimal_point)

        for i in range(len(analogValues) - 2, -1, -1):
            prev = PointerEvalAnalogNew(float(analogValues[i]), prev)
            result = str(prev) + result
        return result

    if CNNType == "Digital":
        for i in range(len(analogValues)):
            if int(analogValues[i]) >= 10:
                result += INVALID_DIGIT
            else:
                result += str(analogValues[i])
        return result

    if CNNType in {"DoubleHyprid10", "Digital100"}:
        number = float(analogValues[-1])
        if number >= 0:
            if extendedResolution:
                result_after_decimal_point = int(number * 10) % 10
                result_before_decimal_point = int(number) % 10
                result = str(result_before_decimal_point) + str(
                    result_after_decimal_point
                )
                prev = result_before_decimal_point
                logger.debug(
                    f"getReadout(dig100-ext) "
                    f"result_before_decimal_point={result_before_decimal_point}, "
                    f"result_after_decimal_point={result_after_decimal_point}, "
                    f"prev={prev}"
                )
            else:
                if beforeNarrowAnalog >= 0:
                    prev = PointerEvalHybridNew(
                        float(analogValues[-1]),
                        beforeNarrowAnalog,
                        prev,
                        True,
                        analogDigitalTransitionStart,
                    )
                else:
                    prev = PointerEvalHybridNew(float(analogValues[-1]), prev, prev)
                result = str(prev)
                logger.debug(f"getReadout(dig100) prev={prev}")
        else:
            result = INVALID_DIGIT
            if extendedResolution and CNNType != "Digital":
                result = "NN"

        for i in range(len(analogValues) - 2, -1, -1):
            if analogValues[i].result_float >= 0:
                prev = PointerEvalHybridNew(
                    float(analogValues[i]), float(analogValues[i + 1]), prev
                )
                logger.debug(f"getReadout#PointerEvalHybridNew()={prev}")
                result = str(prev) + result
                logger.debug(f"getReadout#result={result}")
            else:
                prev = -1
                result = f"N{result}"
                logger.debug(
                    f"getReadout(result_float<0 /'N')  "
                    f"result_float={float(analogValues[i])}"
                )

        return result

    return result


def PointerEvalAnalogNew(number, numeral_preceder):
    if numeral_preceder == -1:
        result = int(number)
        logger.debug(
            f"PointerEvalAnalogNew - No predecessor - Result = {result}, "
            f"number: {number}, numeral_preceder = {numeral_preceder}, "
            f"ANALOG_ERROR = {ANALOG_ERROR}"
        )
        return result

    number_min = number - ANALOG_ERROR / 10.0
    number_max = number + ANALOG_ERROR / 10.0

    if int(number_max) - int(number_min) != 0:
        if numeral_preceder <= ANALOG_ERROR:
            result = (int(number_max) + 10) % 10
            logger.debug(
                f"PointerEvalAnalogNew - number ambiguous, correction upwards - "
                f"result = {result}, number: {number}, "
                f"numeral_preceder = {numeral_preceder}, ANALOG_ERROR = {ANALOG_ERROR}"
            )
            return result
        if numeral_preceder >= 10 - ANALOG_ERROR:
            result = (int(number_min) + 10) % 10
            logger.debug(
                f"PointerEvalAnalogNew - number ambiguous, downward correction - "
                f"result = {result}, number: {number}, "
                f"numeral_preceder = {numeral_preceder}, ANALOG_ERROR = {ANALOG_ERROR}"
            )
            return result

    result = (int(number) + 10) % 10
    logger.debug(
        f"PointerEvalAnalogNew - number unambiguous, no correction necessary - "
        f"result = {result}, number: {number}, "
        f"numeral_preceder = {numeral_preceder}, ANALOG_ERROR = {ANALOG_ERROR}"
    )
    return result


def PointerEvalHybridNew(
    number,
    number_of_predecessors,
    eval_predecessors,
    Analog_Predecessors,
    digitalAnalogTransitionStart,
):
    result_after_decimal_point = (int(number * 10)) % 10
    result_before_decimal_point = (int(number) + 10) % 10

    if eval_predecessors < 0:
        result = int(math.trunc(round((number + 10 % 10) * 100)) / 100)
        logger.debug(
            f"PointerEvalHybridNew - No predecessor - Result = {result}, "
            f"number: {number}, number_of_predecessors = {number_of_predecessors}, "
            f"eval_predecessors = {eval_predecessors}, "
            f"DIGITAL_UNCERTAINTY = {DIGITAL_UNCERTAINTY}"
        )
        return result

    if Analog_Predecessors:
        result = PointerEvalAnalogToDigitNew(
            number,
            number_of_predecessors,
            eval_predecessors,
            digitalAnalogTransitionStart,
        )
        logger.debug(
            f"PointerEvalHybridNew - Analog predecessor, evaluation over "
            f"PointerEvalAnalogNew = {result}, number: {number}, "
            f"number_of_predecessors = {number_of_predecessors}, "
            f"eval_predecessors = {eval_predecessors}, "
            f"DIGITAL_UNCERTAINTY = {DIGITAL_UNCERTAINTY}"
        )
        return result

    if (
        number_of_predecessors >= DIGITAL_TRANSITION_AREA_PREDECESSOR
        and number_of_predecessors <= (10.0 - DIGITAL_TRANSITION_AREA_PREDECESSOR)
    ):
        if (
            result_after_decimal_point <= DIGITAL_BAND
            or result_after_decimal_point >= (10 - DIGITAL_BAND)
        ):
            result = (int(round(number)) + 10) % 10
        else:
            result = (int(math.trunc(number)) + 10) % 10

        logger.debug(
            "PointerEvalHybridNew - NO analogue predecessor, no change of digits, "
            f"as pre-decimal point far enough away = {result}, number: {number}, "
            f"number_of_predecessors = {number_of_predecessors}, "
            f"eval_predecessors = {eval_predecessors}, "
            f"DIGITAL_UNCERTAINTY = {DIGITAL_UNCERTAINTY}"
        )
        return result

    if eval_predecessors <= 1:
        if result_after_decimal_point > 5:
            result = (result_before_decimal_point + 1) % 10
        else:
            result = result_before_decimal_point % 10

        logger.debug(
            "PointerEvalHybridNew - NO analogue predecessor, zero crossing has taken "
            f"placen = {result}, number: {number}, "
            f"number_of_predecessors = {number_of_predecessors}, "
            f"eval_predecessors = {eval_predecessors}, "
            f"DIGITAL_UNCERTAINTY = {DIGITAL_UNCERTAINTY}"
        )
        return result

    if (
        DIGITAL_TRANSITION_AREA_FORWARD >= number_of_predecessors
        or result_after_decimal_point >= 4
    ):
        result = result_before_decimal_point % 10
    else:
        result = (result_before_decimal_point - 1 + 10) % 10

    logger.debug(
        "PointerEvalHybridNew - O analogue predecessor, >= 9.5 --> no zero crossing "
        f"yet = {result}, number: {number}, "
        f"number_of_predecessors = {number_of_predecessors}, "
        f"eval_predecessors = {eval_predecessors}, "
        f"DIGITAL_UNCERTAINTY = {DIGITAL_UNCERTAINTY}, "
        f"result_after_decimal_point = {result_after_decimal_point}"
    )
    return result


def PointerEvalAnalogToDigitNew(
    number, numeral_preceder, eval_predecessors, analogDigitalTransitionStart
):
    result_after_decimal_point = (int(number * 10)) % 10
    result_before_decimal_point = (int(number) + 10) % 10
    roundedUp = False

    if result_after_decimal_point >= (10 - DIGITAL_UNCERTAINTY * 10) or (
        eval_predecessors <= 4 and result_after_decimal_point >= 6
    ):
        result = (int(round(number)) + 10) % 10
        roundedUp = True
        result_after_decimal_point = (int(round(result * 10))) % 10
        result_before_decimal_point = (int(round(result)) + 10) % 10
        logger.debug(
            "PointerEvalAnalogToDigitNew - Digital Uncertainty - Result = {result}, "
            f"number: {number}, numeral_preceder: {numeral_preceder}, "
            f"erg before comma: {result_before_decimal_point}, "
            f"erg after comma: {result_after_decimal_point}"
        )
    else:
        result = (int(math.trunc(number)) + 10) % 10
        logger.debug(
            f"PointerEvalAnalogToDigitNew - NO digital Uncertainty - "
            f"Result = {result}, number: {number}, "
            f"numeral_preceder = {numeral_preceder}"
        )

    if (
        eval_predecessors >= 6
        and (numeral_preceder > analogDigitalTransitionStart or numeral_preceder <= 0.2)
        and roundedUp
    ):
        result = ((result_before_decimal_point + 10) - 1) % 10
        logger.debug(
            "PointerEvalAnalogToDigitNew - "
            f"Nulldurchgang noch nicht stattgefunden = {result}, number: {number}, "
            f"numeral_preceder = {numeral_preceder}, "
            f"eerg after comma = {result_after_decimal_point}"
        )

    return result
