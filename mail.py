# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
'''
Send Mail
'''
from nipype.interfaces.base import (
    BaseInterface, traits, TraitedSpec, 
    BaseInterfaceInputSpec, isdefined, DynamicTraitedSpec, Undefined)


class MailMsgInputSpec(DynamicTraitedSpec, BaseInterfaceInputSpec):
    From = traits.String(
        mandatory=True, desc='From: e-mail adress')
    To   = traits.String(mandatory=True, desc="To: e-mail adress")
    Body = traits.String(mandatory=True, desc="Messsage body")
    Subject = traits.String(mandatory=True, desc="Message subject")

    _outputs = traits.Dict(traits.Any, value={}, usedefault=True)

    def __setattr__(self, key, value):
        if key not in self.copyable_trait_names():
            if not isdefined(value):
                super(MailMsgInputSpec, self).__setattr__(key, value)
            self._outputs[key] = value
        else:
            if key in self._outputs:
                self._outputs[key] = value
            super(MailMsgInputSpec, self).__setattr__(key, value)


class MailMsgOutputSpec(TraitedSpec):
    msg = traits.Any(desc='E-mail Message as Byte object')


class MailMsg(BaseInterface):
    """Simple interface to cretae an e-mail object.

    Example
    -------

    >>> from cni.mail import MailMsg
    >>> mail = MailMsg()
    >>> mail.inputs.From    = "foo@bar.com"
    >>> mail.inputs.To      = "example@site.com, other@site.com"
    >>> mail.inputs.Subject = "Hello World"
    >>> mail.inputs.Body    = "My e-mail body"
    >>> mail.run() # doctest: +SKIP
    """
    input_spec  = MailMsgInputSpec
    output_spec = MailMsgOutputSpec

    def __init__(self, infields=None, force_run=True, **kwargs):
        super(MailMsg, self).__init__(**kwargs)
        undefined_traits = {}
        self._infields = infields

        if infields:
            for key in infields:
                self.inputs.add_trait(key, traits.Any)
                self.inputs._outputs[key] = Undefined
                undefined_traits[key] = Undefined
        self.inputs.trait_set(trait_change_notify=False, **undefined_traits)

        if force_run:
            self._always_run = True

    def _run_interface(self, runtime):
        from email.mime.multipart import MIMEMultipart
        from email.mime.application import MIMEApplication
        from email.mime.text import MIMEText
        from os.path import basename

        self.msg = MIMEMultipart()

        input_dict = {}
        for key, val in list(self.inputs._outputs.items()):
            # expand lists to several columns
            if key == 'trait_added' and val in self.inputs.copyable_trait_names(
            ):
                continue

            if isinstance(val, list):
                for i, v in enumerate(val):
                    input_dict['%s_%d' % (key, i)] = v
            else:
                input_dict[key] = val
        # use input_dict for attachments
        self.msg["Subject"] = self.inputs.Subject
        self.msg["From"]    = self.inputs.From
        self.msg["To"]      = self.inputs.To
        self.msg.attach(MIMEText(self.inputs.Body))

        for fname in input_dict.values():
            with open(fname, 'rb') as f:
                part = MIMEApplication(f.read(),
                        Name=basename(fname))
            # After the file is closed
            part['Content-Disposition'] = 'attachment; filename="%s"' % basename(fname)
            self.msg.attach(part)

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['msg'] = self.msg.as_bytes()
        return outputs

    def _outputs(self):
        return self._add_output_traits(super(MailMsg, self)._outputs())

    def _add_output_traits(self, base):
        return base


class UnixSendmailInputSpec(BaseInterfaceInputSpec):
    msg  = traits.Bytes(mandatory=True, desc='Mail message as byte')

class UnixSendmailOutputSpec(TraitedSpec):
    error = traits.Tuple(desc='Error message')


class UnixSendmail(BaseInterface):
    """Simple interface to send an e-mail with /usr/bin/sendmail

    Example
    -------

    >>> from cni.mail import UnixSendmail
    >>> send = UnixSendmail()
    >>> send.inputs.msg    =  msg # as_byte()
    >>> send.run() # doctest: +SKIP
    """
    input_spec  = UnixSendmailInputSpec
    output_spec = UnixSendmailOutputSpec


    def _run_interface(self, runtime):
        from subprocess import Popen, PIPE
        p=Popen(["/usr/sbin/sendmail", "-t", "-oi"], stdin=PIPE)
        self.error = p.communicate(self.inputs.msg)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['error'] = self.error
        return outputs
