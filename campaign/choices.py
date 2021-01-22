''' campaign status enums'''

class CampaignStatusType():
    '''
    Enum for Campaign Status
    '''
    EXPIRED = 0
    NOT_OPTED = 1
    OPTED = 2

    choices = {
        (EXPIRED, 'EXPIRED'),
        (NOT_OPTED, 'NOT_OPTED'),
        (OPTED, 'OPTED'),

    }

class CampaignOptStatusType():
    '''
    Enum for Campaign Opt Status
    '''
    CLAIMED = 1
    ABOVE_80 = 2
    BELOW_80 = 3

    choices = {
        (CLAIMED, 'CLAIMED'),
        (ABOVE_80, 'ABOVE_80'),
        (BELOW_80, 'BELOW_80'),
    }

class EvidenceStatusType():
    '''
    Enum for Evidence Status
    '''
    ACCEPTED = 1
    REJECTED = 2
    AWAITING_APPROVAL = 3
    OUTSTANDING = 5

    choices = {
        (ACCEPTED, 'Accepted'),
        (REJECTED, 'Rejected'),
        (AWAITING_APPROVAL, 'Awaiting approval'),
        (OUTSTANDING, 'To be submitted'),
    }

class EvidenceStatusCheckType():
    '''
    Enum for Evidence Status
    '''
    ACCEPTED = 1
    REJECTED = 2
    AWAITING_APPROVAL = 3
    RE_SUBMISSION = 4
    OUTSTANDING = 5

    choices = {
        (ACCEPTED, 'ACCEPTED'),
        (REJECTED, 'REJECTED'),
        (AWAITING_APPROVAL, 'AWAITING_APPROVAL'),
        (RE_SUBMISSION, 'RE_SUBMISSION'),
        (OUTSTANDING, 'OUTSTANDING'),
    }