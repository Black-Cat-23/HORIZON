"""HORIZON Video & Synthetic Frame Sources Package."""
from .frame_source import FrameSource, VideoMetadata
from .video_source import VideoFrameSource
from .frame_packet import FramePacket
from .external_video_source import ExternalVideoSource
from .virtual_camera_adapter import VirtualCameraFrameAdapter
from .csv_aligner import GroundTruthCSVAligner, GroundTruthSample
from .video_geometry import (
    CoordinatePoint,
    CoordinateSpace,
    TransformationMethod,
    TransformationParameters,
    VideoGeometryTransformer,
)
from .video_timebase import VideoFrameTiming, VideoTimebase
from .video_pipeline import ExternalHybridPipeline, PipelineMeasurementRecord
from .temporal_consistency import JumpCause, JumpDiagnosis, TemporalConsistencyAnalyzer
from .dynamic_roi import DynamicROI, DynamicROIManager
from .error_budget import (
    ComponentStatistics,
    ComponentStatus,
    ErrorBudgetAnalyzer,
    ErrorBudgetSummary,
    ErrorComponentValue,
    FrameErrorBudget,
)
from .ablation_study import (
    ABLATION_CONFIGURATIONS,
    AblationComparisonReport,
    AblationConfigID,
    AblationConfiguration,
    AblationHarness,
    AblationTrialMetrics,
)
from .robustness_envelope import (
    Benchmark2RobustnessReport,
    CurvePoint,
    RobustnessCurve,
    RobustnessEnvelopeHarness,
    RobustnessRegion,
)
from .run_manifest import (
    HORIZON_VERSION,
    Benchmark2RunManifest,
    Benchmark2RunManager,
    compute_file_sha256,
    generate_benchmark2_artifacts,
    get_hardware_runtime_info,
    get_model_version_info,
    get_software_version_info,
    get_timing_policy_info,
    verify_run_reproducibility,
)
from .source_independent_validation import (
    DiagnosticCategory,
    FrameComparisonRecord,
    SourceIndependenceReport,
    SourceIndependentValidator,
)
from .final_benchmark import (
    FinalExternalBenchmarkReport,
    FinalExternalVideoBenchmark,
    VideoBenchmarkResult,
)



__all__ = [
    "FrameSource",
    "VideoMetadata",
    "VideoFrameSource",
    "FramePacket",
    "ExternalVideoSource",
    "VirtualCameraFrameAdapter",
    "GroundTruthCSVAligner",
    "GroundTruthSample",
    "CoordinatePoint",
    "CoordinateSpace",
    "TransformationMethod",
    "TransformationParameters",
    "VideoGeometryTransformer",
    "VideoFrameTiming",
    "VideoTimebase",
    "ExternalHybridPipeline",
    "PipelineMeasurementRecord",
    "JumpCause",
    "JumpDiagnosis",
    "TemporalConsistencyAnalyzer",
    "DynamicROI",
    "DynamicROIManager",
    "ComponentStatistics",
    "ComponentStatus",
    "ErrorBudgetAnalyzer",
    "ErrorBudgetSummary",
    "ErrorComponentValue",
    "FrameErrorBudget",
    "ABLATION_CONFIGURATIONS",
    "AblationComparisonReport",
    "AblationConfigID",
    "AblationConfiguration",
    "AblationHarness",
    "AblationTrialMetrics",
    "Benchmark2RobustnessReport",
    "CurvePoint",
    "RobustnessCurve",
    "RobustnessEnvelopeHarness",
    "RobustnessRegion",
    "HORIZON_VERSION",
    "Benchmark2RunManifest",
    "Benchmark2RunManager",
    "compute_file_sha256",
    "generate_benchmark2_artifacts",
    "get_hardware_runtime_info",
    "get_model_version_info",
    "get_software_version_info",
    "get_timing_policy_info",
    "verify_run_reproducibility",
    "DiagnosticCategory",
    "FrameComparisonRecord",
    "SourceIndependenceReport",
    "SourceIndependentValidator",
    "FinalExternalBenchmarkReport",
    "FinalExternalVideoBenchmark",
    "VideoBenchmarkResult",
]



