from selfdrive.car.mazda import mazdacan
from selfdrive.car.mazda.values import CAR, DBC
from selfdrive.can.packer import CANPacker
from selfdrive.car import apply_std_steer_torque_limits


class CarControllerParams():
  def __init__(self, car_fingerprint):
    self.STEER_MAX = 600                 # max_steer 2048
    self.STEER_STEP = 1                  # how often we update the steer cmd
    self.STEER_DELTA_UP = 10             # torque increase per refresh
    self.STEER_DELTA_DOWN = 20           # torque decrease per refresh
    if car_fingerprint == CAR.CX5:
      self.STEER_DRIVER_ALLOWANCE = 15   # allowed driver torque before start limiting
    else:
      self.STEER_DRIVER_ALLOWANCE = 15   # allowed driver torque before start limiting
    self.STEER_DRIVER_MULTIPLIER = 1     # weight driver torque heavily
    self.STEER_DRIVER_FACTOR = 1         # from dbc



class CarController():
  def __init__(self, canbus, car_fingerprint):
    self.start_time = 0
    self.lkas_active = False
    self.steer_idx = 0
    self.apply_steer_last = 0
    self.car_fingerprint = car_fingerprint

    # Setup detection helper. Routes commands to
    # an appropriate CAN bus number.
    self.canbus = canbus
    self.params = CarControllerParams(car_fingerprint)
    self.packer_pt = CANPacker(DBC[car_fingerprint]['pt'])

    self.ldw = 0

  def update(self, enabled, CS, frame, actuators):
    """ Controls thread """

    P = self.params

    # Send CAN commands.
    can_sends = []
    canbus = self.canbus

    ### STEER ###

    if (frame % P.STEER_STEP) == 0:

      final_steer = actuators.steer if enabled else 0.
      apply_steer = int(round(final_steer * P.STEER_MAX))

      # limits due to driver torque

      apply_steer = int(round(apply_steer))
      apply_steer = apply_std_steer_torque_limits(apply_steer, self.apply_steer_last, CS.steer_torque_driver, P)

      lkas_enabled = enabled and not CS.steer_not_allowed

      if not lkas_enabled:
        apply_steer = 0

      self.apply_steer_last = apply_steer

      #counts from 0 to 15 then back to 0
      ctr = (frame // P.STEER_STEP) % 16

      if CS.v_ego_raw > 14:
        line_not_visible = 0
      else:
        line_not_visible = 1

      e1 = 0 #CS.CAM_LKAS.err1
      e2 = 0 #CS.CAM_LKAS.err2

      can_sends.append(mazdacan.create_steering_control(self.packer_pt, canbus.powertrain,
                                                        CS.CP.carFingerprint, ctr, apply_steer,
                                                        line_not_visible,
                                                        1, 1, e1, e2, self.ldw))
      # send lane info msgs at 1/8 rate of steer msgs
      #if (ctr % 8 == 0):
      #  can_sends.append(mazdacan.create_cam_lane_info(self.packer_pt, canbus.powertrain, CS.CP.carFingerprint,
      #                                                 line_not_visible, CS.cam_laneinfo, CS.steer_lkas,
      #                                                 self.ldwr, self.ldwl, lines))

      #can_sends.append(mazdacan.create_lkas_msg(self.packer_pt, canbus.powertrain, CS.CP.carFingerprint, CS.CAM_LKAS))

      #can_sends.append(mazdacan.create_lane_track(self.packer_pt, canbus.powertrain, CS.CP.carFingerprint, CS.CAM_LT))

    return can_sends
