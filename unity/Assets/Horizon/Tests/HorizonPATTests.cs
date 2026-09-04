using System;
using UnityEngine;
using Horizon.Math;
using Horizon.Simulation;
using Horizon.Perception;
using Horizon.Estimation;
using Horizon.Control;

namespace Horizon.Tests
{
    /// <summary>
    /// Automated test suite validating mathematical correctness, optical projection,
    /// actuator dynamics, and deterministic simulation repeatability.
    /// </summary>
    public static class HorizonPATTests
    {
        public static bool RunAllTests(out string testReport)
        {
            System.Text.StringBuilder sb = new System.Text.StringBuilder();
            sb.AppendLine("=== HORIZON PAT VERIFICATION TEST SUITE ===");

            bool allPassed = true;
            allPassed &= TestOpticalAxisZeroError(sb);
            allPassed &= TestSymmetricAngularOffset(sb);
            allPassed &= TestActuatorVelocitySaturation(sb);
            allPassed &= TestActuatorAccelerationSaturation(sb);
            allPassed &= TestActuatorTransportLatency(sb);
            allPassed &= TestScenarioDeterminism(sb);

            testReport = sb.ToString();
            return allPassed;
        }

        private static bool TestOpticalAxisZeroError(System.Text.StringBuilder sb)
        {
            CameraIntrinsics intrinsics = new CameraIntrinsics(1920, 1080, 40.0f);
            Vector3 targetBoresight = new Vector3(0.0f, 0.0f, 50.0f);

            bool projected = intrinsics.WorldToPixel(targetBoresight, out Vector2 pixel);
            Vector2 angles = intrinsics.PixelToAnglesDeg(pixel);

            bool passed = projected &&
                          Mathf.Abs(pixel.x - 960.0f) < 0.001f &&
                          Mathf.Abs(pixel.y - 540.0f) < 0.001f &&
                          Mathf.Abs(angles.x) < 0.001f &&
                          Mathf.Abs(angles.y) < 0.001f;

            sb.AppendLine($"[TEST 1] Optical Axis Zero Error: {(passed ? "PASSED" : "FAILED")} (Angles: {angles.x:F4}, {angles.y:F4} deg)");
            return passed;
        }

        private static bool TestSymmetricAngularOffset(System.Text.StringBuilder sb)
        {
            CameraIntrinsics intrinsics = new CameraIntrinsics(1920, 1080, 40.0f);
            Vector3 targetRight = new Vector3(10.0f, 0.0f, 50.0f);
            Vector3 targetLeft = new Vector3(-10.0f, 0.0f, 50.0f);

            intrinsics.WorldToPixel(targetRight, out Vector2 pxRight);
            intrinsics.WorldToPixel(targetLeft, out Vector2 pxLeft);

            Vector2 angRight = intrinsics.PixelToAnglesDeg(pxRight);
            Vector2 angLeft = intrinsics.PixelToAnglesDeg(pxLeft);

            bool passed = Mathf.Abs(angRight.x + angLeft.x) < 0.001f && angRight.x > 0.0f;
            sb.AppendLine($"[TEST 2] Symmetric Angular Offset: {(passed ? "PASSED" : "FAILED")} (+{angRight.x:F3} deg, {angLeft.x:F3} deg)");
            return passed;
        }

        private static bool TestActuatorVelocitySaturation(System.Text.StringBuilder sb)
        {
            ActuatorDynamics actuator = new ActuatorDynamics();
            actuator.MaxAngularVelocityDegPerSec = 45.0f;
            actuator.LatencySeconds = 0.0f;

            Vector2 excessiveCommand = new Vector2(200.0f, -150.0f);
            Vector2 deltaAngle = actuator.Update(excessiveCommand, 0.05f, 0.05f);

            float executedSpeed = deltaAngle.magnitude / 0.05f;
            bool passed = actuator.CurrentVelocity.x <= 45.001f && actuator.CurrentVelocity.y >= -45.001f;

            sb.AppendLine($"[TEST 3] Velocity Saturation (Limit 45 deg/s): {(passed ? "PASSED" : "FAILED")} (Executed: {actuator.CurrentVelocity.x:F1}, {actuator.CurrentVelocity.y:F1} deg/s)");
            return passed;
        }

        private static bool TestActuatorAccelerationSaturation(System.Text.StringBuilder sb)
        {
            ActuatorDynamics actuator = new ActuatorDynamics();
            actuator.MaxAngularVelocityDegPerSec = 100.0f;
            actuator.MaxAngularAccelDegPerSec2 = 120.0f;
            actuator.LatencySeconds = 0.0f;

            float dt = 0.02f;
            Vector2 stepCommand = new Vector2(100.0f, 0.0f);
            actuator.Update(stepCommand, dt, dt);

            // In 0.02s at max 120 deg/s^2, max velocity change is 120 * 0.02 = 2.4 deg/s
            float maxExpectedVel = 120.0f * dt;
            bool passed = actuator.CurrentVelocity.x <= (maxExpectedVel + 0.001f);

            sb.AppendLine($"[TEST 4] Acceleration Saturation (Limit 120 deg/s^2): {(passed ? "PASSED" : "FAILED")} (Achieved in {dt}s: {actuator.CurrentVelocity.x:F2} deg/s, Max Allowed: {maxExpectedVel:F2} deg/s)");
            return passed;
        }

        private static bool TestActuatorTransportLatency(System.Text.StringBuilder sb)
        {
            ActuatorDynamics actuator = new ActuatorDynamics();
            actuator.LatencySeconds = 0.10f; // 100ms latency

            Vector2 cmd = new Vector2(30.0f, 0.0f);
            actuator.Update(cmd, 0.02f, 0.02f);
            actuator.Update(cmd, 0.02f, 0.04f);
            actuator.Update(cmd, 0.02f, 0.06f);

            // Before 100ms, velocity must still be 0
            bool zeroBeforeDelay = actuator.CurrentVelocity.x < 0.001f;

            // Advance past 100ms
            actuator.Update(cmd, 0.02f, 0.08f);
            actuator.Update(cmd, 0.02f, 0.10f);
            actuator.Update(cmd, 0.02f, 0.12f);

            bool activeAfterDelay = actuator.CurrentVelocity.x > 0.0f;
            bool passed = zeroBeforeDelay && activeAfterDelay;

            sb.AppendLine($"[TEST 5] Actuator Latency Delay (100ms delay): {(passed ? "PASSED" : "FAILED")}");
            return passed;
        }

        private static bool TestScenarioDeterminism(System.Text.StringBuilder sb)
        {
            ScenarioEngine simA = new GameObject("SimA").AddComponent<ScenarioEngine>();
            ScenarioEngine simB = new GameObject("SimB").AddComponent<ScenarioEngine>();

            simA.InitializeScenario(12345);
            simB.InitializeScenario(12345);

            for (int i = 0; i < 100; i++)
            {
                simA.StepSimulation(0.05f);
                simB.StepSimulation(0.05f);
            }

            float diff = Vector3.Distance(simA.GroundTruthPosition, simB.GroundTruthPosition);
            bool passed = diff < 0.0001f;

            GameObject.DestroyImmediate(simA.gameObject);
            GameObject.DestroyImmediate(simB.gameObject);

            sb.AppendLine($"[TEST 6] Determinism Across Identical Seed (100 steps): {(passed ? "PASSED" : "FAILED")} (Position Difference: {diff:E6} m)");
            return passed;
        }
    }
}
