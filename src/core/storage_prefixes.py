def _partition(name: str, value: int | str | None) -> str:
    return f"{name}_{value}"


def attorney_prefix(*, rsrc_no: int, job_no: int, attorney_id: int) -> str:
    return "/".join(
        [
            "attorneys",
            _partition("rsrc_no", rsrc_no),
            _partition("job_no", job_no),
            _partition("attorney_id", attorney_id),
        ]
    )


def billing_prefix(*, rsrc_no: int, job_no: int, billing_id: int) -> str:
    return "/".join(
        [
            "billings",
            _partition("rsrc_no", rsrc_no),
            _partition("job_no", job_no),
            _partition("billing_id", billing_id),
        ]
    )


def equipment_time_prefix(*, rsrc_no: int, job_no: int, equipment_time_id: int) -> str:
    return "/".join(
        [
            "equipment_time",
            _partition("rsrc_no", rsrc_no),
            _partition("job_no", job_no),
            _partition("equipment_time_id", equipment_time_id),
        ]
    )


def profile_picture_prefix(*, rsrc_no: int) -> str:
    return "/".join(["profile_pictures", _partition("rsrc_no", rsrc_no)])


def temp_video_prefix(*, rsrc_no: int, upload_id: str) -> str:
    return "/".join(["_temp_videos", _partition("rsrc_no", rsrc_no), _partition("upload_id", upload_id)])


def witness_video_prefix(*, rsrc_no: int, job_no: int, witness_id: int, video_id: int) -> str:
    return "/".join(
        [
            "witness_videos",
            _partition("rsrc_no", rsrc_no),
            _partition("job_no", job_no),
            _partition("witness_id", witness_id),
            _partition("video_id", video_id),
        ]
    )


def merged_witness_video_prefix(*, job_no: int, witness_id: int) -> str:
    return "/".join(
        [
            "merged_witness_videos",
            _partition("job_no", job_no),
            _partition("witness_id", witness_id),
        ]
    )
